#!/usr/bin/env python
"""
PRECISION SWEEP — Kaggle GPU runner (self-contained, resumable).

The original thesis experiment: same elitist LLM-proposer loop as the paper's
Arm A, but the proposer is a LOCAL quantized model, swept across precisions:
    q2_k -> q3_k_m -> q4_k_m -> q8_0 -> fp16
Model: Qwen/Qwen2.5-Coder-7B-Instruct-GGUF (official repo, filenames verified
2026-07-17). Deterministic Python evaluator; per-candidate live logging with
reconstructed:false; quantization integrity (sha256 + size) logged per condition.

HOW TO RUN ON KAGGLE
  1. New notebook -> Settings -> Accelerator: GPU T4 x2 (x2 REQUIRED for fp16;
     on a single T4 the script auto-skips fp16 and still runs the 4 quant levels).
     Internet: ON.
  2. Cell 1 (install; prebuilt CUDA wheel first, source build as fallback):
       %pip install -q huggingface_hub
       %pip install -q llama-cpp-python \
           --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu122 \
        || CMAKE_ARGS="-DGGML_CUDA=on" pip install -q llama-cpp-python
  3. Cell 2: upload this file as a Kaggle "Dataset" or paste it with %%writefile,
     then:
       !python kaggle_precision_sweep.py
  4. Results land in /kaggle/working/precision_sweep/ (small, persisted):
       candidates_precision.jsonl   <- THE data, one row per candidate, live
       probes_precision.jsonl      <- zero-shot recall controls per precision
       provenance.json             <- file hashes, sizes, GPU info, timings
       results_precision.json     <- aggregate summary
       state/                     <- per-(precision,seed) checkpoints
     Download the folder when done. Session dies mid-run? Re-run the same cell:
     the script resumes from checkpoints and never rewrites logged rows.

Budget: 5 precisions x (5 seeds x 10 gens + 6 probes) = 280 generations.
Rough wall on T4x2: 4-7 h including downloads. Order runs cheapest-risk first
(q8_0, q4_k_m, q3_k_m, q2_k, fp16 last) so a dead session still leaves a
publishable partial ladder. Each model file is deleted after its condition
finishes to bound disk.
"""

import ast
import gc
import hashlib
import json
import math
import os
import re
import subprocess
import time

# ----------------------------- configuration --------------------------------

REPO = "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF"
PRECISIONS = [  # (label, filename, min_gpus_required)
    ("q8_0",   "qwen2.5-coder-7b-instruct-q8_0.gguf",   1),
    ("q4_k_m", "qwen2.5-coder-7b-instruct-q4_k_m.gguf", 1),
    ("q3_k_m", "qwen2.5-coder-7b-instruct-q3_k_m.gguf", 1),
    ("q2_k",   "qwen2.5-coder-7b-instruct-q2_k.gguf",   1),
    ("fp16",   "qwen2.5-coder-7b-instruct-fp16.gguf",   2),
]
SEEDS = [42, 123, 456, 789, 1111]
GENS = 10                 # matched to the paper's four-arm protocol
PROBES_PER_PRECISION = 6  # zero-shot recall controls
N = 26
EPS = 1e-6
N_CTX = 4096
MAX_TOKENS = 1200
TEMPERATURE = 0.8
TOP_P = 0.95

WORK = "/kaggle/working/precision_sweep"
MODELS_DIR = "/kaggle/tmp/models"      # ephemeral, not persisted (models are big)
STATE_DIR = os.path.join(WORK, "state")
CAND_LOG = os.path.join(WORK, "candidates_precision.jsonl")
PROBE_LOG = os.path.join(WORK, "probes_precision.jsonl")
PROVENANCE = os.path.join(WORK, "provenance.json")
RESULTS = os.path.join(WORK, "results_precision.json")

# Local-run override so the file can be smoke-tested off Kaggle.
if not os.path.isdir("/kaggle"):
    WORK = os.path.abspath("./precision_sweep")
    MODELS_DIR = os.path.abspath("./models")
    STATE_DIR = os.path.join(WORK, "state")
    CAND_LOG = os.path.join(WORK, "candidates_precision.jsonl")
    PROBE_LOG = os.path.join(WORK, "probes_precision.jsonl")
    PROVENANCE = os.path.join(WORK, "provenance.json")
    RESULTS = os.path.join(WORK, "results_precision.json")

# ------------------------- evaluator (mirrors harness.py) --------------------

def parse_proposal(raw):
    """Extract a Python list of 26 [x, y, r] floats from raw model output.
    Returns (circles, error). Mirrors agent-run/harness.py semantics."""
    if raw is None:
        return None, "no_output"
    text = raw.strip()
    text = re.sub(r"```(?:python|json)?", "", text).replace("```", "").strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None, "no_list_found"
    text = text[start:end + 1]
    try:
        obj = ast.literal_eval(text)
    except (ValueError, SyntaxError) as e:
        return None, f"literal_eval: {type(e).__name__}"
    if not isinstance(obj, (list, tuple)):
        return None, "not_a_list"
    circles = []
    for item in obj:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            return None, "bad_triple"
        try:
            circles.append(tuple(float(v) for v in item))
        except (TypeError, ValueError):
            return None, "non_numeric"
    return circles, None


def evaluate(circles):
    res = {"viable": False, "valid": False, "score": 0.0,
           "mean_radius": 0.0, "density": 0.0,
           "n": 0 if circles is None else len(circles)}
    if circles is None:
        return res
    if len(circles) != N or any(r <= 0 for (_, _, r) in circles):
        return res
    res["viable"] = True
    radii = [r for (_, _, r) in circles]
    res["mean_radius"] = sum(radii) / N
    res["density"] = sum(math.pi * r * r for r in radii)
    inside = all(x - r >= -EPS and x + r <= 1 + EPS and
                 y - r >= -EPS and y + r <= 1 + EPS for (x, y, r) in circles)
    overlap = False
    for i in range(N):
        xi, yi, ri = circles[i]
        for j in range(i + 1, N):
            xj, yj, rj = circles[j]
            if math.hypot(xi - xj, yi - yj) + EPS < ri + rj:
                overlap = True
                break
        if overlap:
            break
    if inside and not overlap:
        res["valid"] = True
        res["score"] = sum(radii)
    return res


def baseline_packing():
    """26 circles on a 6x5 grid, r = 0.9/26 — identical to the paper's baseline."""
    r = round(0.9 / N, 6)
    pts = []
    for row in range(5):
        for col in range(6):
            if len(pts) >= N:
                break
            pts.append([round((col + 0.5) / 6.0, 6), round((row + 0.5) / 5.0, 6), r])
    return pts


def self_test():
    base = baseline_packing()
    ev = evaluate([tuple(c) for c in base])
    assert ev["valid"], "baseline must be valid"
    assert abs(ev["score"] - 0.89999) < 1e-4, f"baseline score {ev['score']}"
    bad = [tuple(c) for c in base]
    bad[0] = (bad[0][0], bad[0][1], 0.5)  # giant circle overlaps neighbors
    assert not evaluate(bad)["valid"], "overlap must invalidate"
    c, err = parse_proposal("junk before [[0.1, 0.1, 0.05]] junk after")
    assert err is None and len(c) == 1, "parser must extract bracketed list"
    print("[selftest] evaluator + parser OK")


# ------------------------------ prompts --------------------------------------

def loop_prompt(best_circles, best_score):
    packing = json.dumps([[round(x, 6), round(y, 6), round(r, 6)]
                          for (x, y, r) in best_circles])
    return (
        "You are the proposal step of an evolutionary search for circle packings.\n"
        f"Current best packing (sum of radii = {best_score:.6f}):\n{packing}\n\n"
        f"Produce a packing of exactly {N} circles with a HIGHER sum of radii.\n"
        "MUST hold: exactly 26 circles; every circle fully inside the unit square "
        "[0,1]x[0,1] (x-r >= 0, x+r <= 1, same for y); no two circles overlap "
        "(distance between centers >= sum of the two radii; touching is allowed).\n"
        "Output ONLY the raw Python list of 26 [x, y, r] lists. No explanation, "
        "no code fences, no other text."
    )


PROBE_PROMPT = (
    f"Pack exactly {N} non-overlapping circles inside the unit square [0,1]x[0,1] "
    "so that the sum of their radii is as large as possible. Every circle must lie "
    "fully inside the square; circles may touch but not overlap.\n"
    "Output ONLY the raw Python list of 26 [x, y, r] lists. No explanation, "
    "no code fences, no other text."
)

# ------------------------------ plumbing -------------------------------------

def sha256_file(path, buf=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def gpu_info():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        gpus = [l.strip() for l in out.splitlines() if l.strip()]
        return gpus
    except Exception:
        return []


def append_jsonl(path, row):
    with open(path, "a") as f:
        f.write(json.dumps(row) + "\n")
        f.flush()
        os.fsync(f.fileno())


def load_provenance():
    if os.path.exists(PROVENANCE):
        with open(PROVENANCE) as f:
            return json.load(f)
    return {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "gpus": gpu_info(),
            "repo": REPO, "gens": GENS, "seeds": SEEDS,
            "temperature": TEMPERATURE, "top_p": TOP_P, "conditions": {}}


def save_provenance(p):
    with open(PROVENANCE, "w") as f:
        json.dump(p, f, indent=2)


def spath(quant, seed):
    return os.path.join(STATE_DIR, f"{quant}_seed_{seed}.json")


def load_state(quant, seed):
    p = spath(quant, seed)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    base = baseline_packing()
    ev = evaluate([tuple(c) for c in base])
    return {"quant": quant, "seed": seed, "gen": 0,
            "best_circles": base, "best_score": ev["score"]}


def save_state(st):
    with open(spath(st["quant"], st["seed"]), "w") as f:
        json.dump(st, f)


def count_probes_done(quant):
    if not os.path.exists(PROBE_LOG):
        return 0
    with open(PROBE_LOG) as f:
        return sum(1 for l in f if json.loads(l)["quant"] == quant)


# --------------------------- model management --------------------------------

def download_model(fname):
    from huggingface_hub import hf_hub_download
    os.makedirs(MODELS_DIR, exist_ok=True)
    print(f"[download] {fname} ...")
    t0 = time.time()
    path = hf_hub_download(repo_id=REPO, filename=fname, local_dir=MODELS_DIR)
    print(f"[download] done in {time.time()-t0:.0f}s -> {path}")
    return path


def load_llm(path, n_gpus):
    from llama_cpp import Llama
    kwargs = dict(model_path=path, n_gpu_layers=-1, n_ctx=N_CTX, verbose=False)
    if n_gpus > 1:
        kwargs["split_mode"] = 1  # split layers across all visible GPUs
    print(f"[load] {os.path.basename(path)} (gpus={n_gpus})")
    t0 = time.time()
    llm = Llama(**kwargs)
    print(f"[load] ready in {time.time()-t0:.0f}s")
    return llm


def generate(llm, prompt, seed_val):
    t0 = time.time()
    try:
        out = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=MAX_TOKENS, temperature=TEMPERATURE, top_p=TOP_P,
            seed=seed_val)
        text = out["choices"][0]["message"]["content"]
        usage = out.get("usage", {})
    except Exception as e:
        return None, f"gen_error: {type(e).__name__}: {e}", 0, time.time() - t0
    return text, None, usage.get("completion_tokens", 0), time.time() - t0


# ------------------------------ main sweep -----------------------------------

def run_condition(quant, fname, min_gpus, provenance):
    n_gpus = len(provenance["gpus"])
    if n_gpus < min_gpus:
        print(f"[skip] {quant}: needs {min_gpus} GPU(s), have {n_gpus}")
        provenance["conditions"].setdefault(quant, {})["skipped"] = \
            f"needs {min_gpus} gpus, have {n_gpus}"
        save_provenance(provenance)
        return

    states = {s: load_state(quant, s) for s in SEEDS}
    probes_done = count_probes_done(quant)
    loop_done = all(st["gen"] >= GENS for st in states.values())
    if loop_done and probes_done >= PROBES_PER_PRECISION:
        print(f"[done] {quant}: already complete, skipping")
        return

    path = download_model(fname)
    cond = provenance["conditions"].setdefault(quant, {})
    if "sha256" not in cond:
        print(f"[hash] {quant} ...")
        cond["sha256"] = sha256_file(path)
        cond["bytes"] = os.path.getsize(path)
        cond["filename"] = fname
        save_provenance(provenance)
        print(f"[hash] {cond['sha256'][:16]}... ({cond['bytes']/1e9:.2f} GB)")

    llm = load_llm(path, n_gpus)
    try:
        # Loop candidates: generation-major order so a dead session leaves every
        # seed at a comparable depth instead of one finished seed and four empty.
        for gen in range(GENS):
            for s in SEEDS:
                st = states[s]
                if st["gen"] != gen:
                    continue  # resumed past this point already
                prompt = loop_prompt([tuple(c) for c in st["best_circles"]],
                                     st["best_score"])
                text, gerr, ctoks, wall = generate(llm, prompt, s * 1000 + gen)
                circles, perr = parse_proposal(text) if gerr is None else (None, gerr)
                ev = evaluate(circles)
                row = {"arm": "precision_sweep", "proposer": f"qwen2.5-coder-7b-{quant}",
                       "quant": quant, "seed": s, "gen": gen,
                       "parent_score": round(st["best_score"], 6),
                       "score": round(ev["score"], 6), "viable": ev["viable"],
                       "valid": ev["valid"], "n_circles": ev["n"],
                       "mean_radius": round(ev["mean_radius"], 6),
                       "density": round(ev["density"], 6),
                       "parse_error": perr, "completion_tokens": ctoks,
                       "wall_s": round(wall, 2), "reconstructed": False}
                append_jsonl(CAND_LOG, row)
                if ev["valid"] and ev["score"] > st["best_score"]:
                    st["best_score"] = ev["score"]
                    st["best_circles"] = [list(c) for c in circles]
                st["gen"] = gen + 1
                save_state(st)
                print(f"[{quant}] seed {s} gen {gen}: score={ev['score']:.6f} "
                      f"viable={ev['viable']} valid={ev['valid']} "
                      f"best={st['best_score']:.6f} ({wall:.0f}s)")

        # Zero-shot probes (recall control at this precision).
        for k in range(probes_done, PROBES_PER_PRECISION):
            text, gerr, ctoks, wall = generate(llm, PROBE_PROMPT, 900000 + k)
            circles, perr = parse_proposal(text) if gerr is None else (None, gerr)
            ev = evaluate(circles)
            append_jsonl(PROBE_LOG, {
                "kind": "zero_shot_probe", "quant": quant, "probe": k,
                "score": round(ev["score"], 6), "viable": ev["viable"],
                "valid": ev["valid"], "n_circles": ev["n"], "parse_error": perr,
                "completion_tokens": ctoks, "wall_s": round(wall, 2),
                "raw": (text or "")[:4000], "reconstructed": False})
            print(f"[{quant}] probe {k}: score={ev['score']:.6f} valid={ev['valid']}")
    finally:
        del llm
        gc.collect()
        try:
            os.remove(path)  # bound disk; hash already recorded
            print(f"[cleanup] removed {fname}")
        except OSError:
            pass


def summarize():
    rows = [json.loads(l) for l in open(CAND_LOG)] if os.path.exists(CAND_LOG) else []
    probes = [json.loads(l) for l in open(PROBE_LOG)] if os.path.exists(PROBE_LOG) else []
    out = {}
    for quant, _, _ in PRECISIONS:
        qr = [r for r in rows if r["quant"] == quant]
        if not qr:
            continue
        per = []
        for s in SEEDS:
            sr = [r for r in qr if r["seed"] == s]
            best = max((r["score"] for r in sr if r["valid"]), default=0.0)
            per.append({"seed": s, "best": round(best, 6), "gens": len(sr),
                        "viable": sum(1 for r in sr if r["viable"]),
                        "valid": sum(1 for r in sr if r["valid"])})
        bests = [p["best"] for p in per]
        mean = sum(bests) / len(bests)
        qp = [p for p in probes if p["quant"] == quant]
        out[quant] = {
            "per_seed": per, "mean_best": round(mean, 6),
            "pop_std_best": round(math.sqrt(
                sum((b - mean) ** 2 for b in bests) / len(bests)), 6),
            "viability": f"{sum(1 for r in qr if r['viable'])}/{len(qr)}",
            "validity": f"{sum(1 for r in qr if r['valid'])}/{len(qr)}",
            "probe_scores": [p["score"] for p in qp],
            "probe_valid": sum(1 for p in qp if p["valid"]),
        }
    with open(RESULTS, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(STATE_DIR, exist_ok=True)
    self_test()
    provenance = load_provenance()
    if not provenance["gpus"]:
        provenance["gpus"] = gpu_info()
    save_provenance(provenance)
    print(f"[gpus] {provenance['gpus'] or 'NONE DETECTED (will be very slow)'}")
    for quant, fname, min_gpus in PRECISIONS:
        print(f"\n===== condition: {quant} =====")
        run_condition(quant, fname, min_gpus, provenance)
        summarize()  # refresh aggregate after every condition
    print("\n[done] all conditions processed. Download /kaggle/working/precision_sweep/")


if __name__ == "__main__":
    main()
