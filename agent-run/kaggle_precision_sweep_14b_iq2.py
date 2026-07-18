#!/usr/bin/env python
# ============================================================================
# PREREGISTERED DECISION RULES — written and pushed BEFORE this run executed.
# (Kaggle version history timestamps this code prior to execution.)
#
# PURPOSE. The novelty cliff observed at 2-bit quantization has so far been
# demonstrated only on the OFFICIAL Qwen Q2_K file (no importance matrix).
# Effective bit-width co-varies with the quantization ALGORITHM, so "the cliff
# is a bit-width effect" is currently really "the cliff is a Q2_K effect".
# This run unbundles the two with TWO conditions from ONE third-party repo
# (bartowski/Qwen2.5-Coder-14B-Instruct-GGUF, imatrix-calibrated):
#   A) Q2_K  (same algorithm class as the original cliff rung, ~3.4 bpw
#      effective, but imatrix-calibrated and independently produced)
#   B) IQ2_M (different algorithm family: IQ non-linear quants, ~2.7 bpw —
#      FEWER bits than Q2_K but typically LOWER perplexity due to imatrix)
#
# Seeds are the values [2222, 3333, 5555, 7777, 9999] used in the fresh-seed
# replication; the WEIGHT FILES differ, so all draws here are new samples
# never observed before. Protocol identical to prior 14B runs.
#
# DECISION RULES (all outcomes informative; none triggers withdrawal):
#  D1 Both bartowski Q2_K and IQ2_M show coordinate-verified parent-echo
#     >= 60% among valid rows  ->  the cliff generalizes across quantization
#     algorithms in the 2-bit class; paper language may generalize from
#     "Q2_K" to "2-bit-class quantization".
#  D2 bartowski Q2_K echoes >= 60% but IQ2_M <= 35%  ->  the cliff tracks
#     quantization QUALITY, not raw bit-width (imatrix IQ2 preserves proposal
#     novelty at fewer bits); paper reports the cliff as algorithm/quality-
#     mediated and keeps "Q2_K" language for the original result.
#  D3 bartowski Q2_K <= 35%  ->  the original cliff is at least partly
#     specific to the official no-imatrix Q2_K file; reported prominently as
#     a limitation of the original finding.
#  Intermediate rates -> inconclusive, reported as such.
#  Must-differ probes (10 per condition, same verbatim prohibition suffix as
#  the fresh run) extend the n=5-per-rung mechanism probe; echo-despite-
#  prohibition at any rung with >= 60% loop echo further supports the
#  degraded-novelty reading at that rung.
# ============================================================================

# --- batch-kernel bootstrap: script kernels have no %pip -------------------
import subprocess as _sp
import sys as _sys

def _pip(*a):
    return _sp.run([_sys.executable, "-m", "pip", "install", "-q", *a]).returncode

_pip("huggingface_hub")
_pip("llama-cpp-python",
     "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cu122")
try:
    import llama_cpp  # noqa: F401
except Exception:
    print("[bootstrap] prebuilt wheel failed; building from source (slow)...")
    import os as _os
    _env = dict(_os.environ, CMAKE_ARGS="-DGGML_CUDA=on")
    _sp.run([_sys.executable, "-m", "pip", "install", "-q",
             "--force-reinstall", "--no-cache-dir", "llama-cpp-python"],
            env=_env, check=True)
    import llama_cpp  # noqa: F401
print("[bootstrap] llama_cpp ready:", llama_cpp.__version__)
# ---------------------------------------------------------------------------
"""
PRECISION SWEEP 14B — IQ2 ALGORITHM CONTROL.

Two conditions (bartowski imatrix Q2_K, bartowski IQ2_M), five seeds,
10 generations each + 10 must-differ probes per condition. Protocol identical
to the archived and fresh-seed 14B runs (same prompts, sampling params,
generation-major order, durable logging: JSONL| console echo, per-candidate
coordinates, per-condition zip).

Budget: 2 quants x 5 seeds x 10 gens = 100 loop + 2 x 10 must-differ = 120
generations. Expected wall on T4 x2: ~1.5-2 h including model downloads.
"""

import ast
import gc
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import time

# ----------------------------- configuration --------------------------------

REPO = "bartowski/Qwen2.5-Coder-14B-Instruct-GGUF"
PRECISIONS = [  # (label, filename, min_gpus_required)
    ("q2_k_imx", "Qwen2.5-Coder-14B-Instruct-Q2_K.gguf",  1),
    ("iq2_m",    "Qwen2.5-Coder-14B-Instruct-IQ2_M.gguf", 1),
]
SEEDS = [2222, 3333, 5555, 7777, 9999]  # new draws: weight files differ
GENS = 10
MUSTDIFFER_PER_PRECISION = 10
N = 26
EPS = 1e-6
N_CTX = 4096
MAX_TOKENS = 1200
TEMPERATURE = 0.8
TOP_P = 0.95
RUNNER_VERSION = "14b_iq2_v1"

WORK = "/kaggle/working/precision_sweep_14b_iq2"
MODELS_DIR = "/kaggle/tmp/models"
ZIP_BASE = "/kaggle/working/precision_sweep_14b_iq2_partial"
STATE_DIR = os.path.join(WORK, "state")
CAND_LOG = os.path.join(WORK, "candidates_precision_14b_iq2.jsonl")
MUSTDIFFER_LOG = os.path.join(WORK, "mustdiffer_14b_iq2.jsonl")
PROVENANCE = os.path.join(WORK, "provenance.json")
RESULTS = os.path.join(WORK, "results_precision_14b_iq2.json")

if not os.path.isdir("/kaggle"):
    WORK = os.path.abspath("./precision_sweep_14b_iq2")
    MODELS_DIR = os.path.abspath("./models")
    ZIP_BASE = os.path.abspath("./precision_sweep_14b_iq2_partial")
    STATE_DIR = os.path.join(WORK, "state")
    CAND_LOG = os.path.join(WORK, "candidates_precision_14b_iq2.jsonl")
    MUSTDIFFER_LOG = os.path.join(WORK, "mustdiffer_14b_iq2.jsonl")
    PROVENANCE = os.path.join(WORK, "provenance.json")
    RESULTS = os.path.join(WORK, "results_precision_14b_iq2.json")

# ------------------------- evaluator (mirrors harness.py) --------------------

def parse_proposal(raw):
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
    bad[0] = (bad[0][0], bad[0][1], 0.5)
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


def must_differ_prompt(best_circles, best_score):
    """Identical to loop_prompt except the appended must-differ constraint —
    the single manipulated variable of the mechanism probe."""
    return (
        loop_prompt(best_circles, best_score) + "\n"
        "IMPORTANT: your packing MUST NOT be identical to the current best "
        "packing shown above. Change the position or radius of at least three "
        "circles. Returning the same packing again counts as failure."
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
        return [l.strip() for l in out.splitlines() if l.strip()]
    except Exception:
        return []


def append_jsonl(path, row):
    """Append to file AND echo to console ("JSONL|" prefix) — console echo is
    the durability layer (version history survives /kaggle/working wipes)."""
    line = json.dumps(row)
    with open(path, "a") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())
    print("JSONL|" + line, flush=True)


def snapshot_zip():
    try:
        shutil.make_archive(ZIP_BASE, "zip", WORK)
        print(f"[zip] snapshot -> {ZIP_BASE}.zip")
    except Exception as e:
        print(f"[zip] FAILED (non-fatal): {type(e).__name__}: {e}")


def load_provenance():
    if os.path.exists(PROVENANCE):
        with open(PROVENANCE) as f:
            return json.load(f)
    return {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "gpus": gpu_info(),
            "repo": REPO, "gens": GENS, "seeds": SEEDS,
            "temperature": TEMPERATURE, "top_p": TOP_P,
            "runner_version": RUNNER_VERSION,
            "purpose": "IQ2 algorithm control: unbundle bit-width from quant algorithm",
            "conditions": {}}


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


def count_mustdiffer_done(quant):
    if not os.path.exists(MUSTDIFFER_LOG):
        return 0
    with open(MUSTDIFFER_LOG) as f:
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
        kwargs["split_mode"] = 1
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
    md_done = count_mustdiffer_done(quant)
    loop_done = all(st["gen"] >= GENS for st in states.values())
    if loop_done and md_done >= MUSTDIFFER_PER_PRECISION:
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
        # seed at a comparable depth.
        for gen in range(GENS):
            for s in SEEDS:
                st = states[s]
                if st["gen"] != gen:
                    continue
                prompt = loop_prompt([tuple(c) for c in st["best_circles"]],
                                     st["best_score"])
                text, gerr, ctoks, wall = generate(llm, prompt, s * 1000 + gen)
                circles, perr = parse_proposal(text) if gerr is None else (None, gerr)
                ev = evaluate(circles)
                row = {"arm": "precision_sweep_14b_iq2",
                       "proposer": f"qwen2.5-coder-14b-{quant}",
                       "quant": quant, "seed": s, "gen": gen,
                       "parent_score": round(st["best_score"], 6),
                       "score": round(ev["score"], 6), "viable": ev["viable"],
                       "valid": ev["valid"], "n_circles": ev["n"],
                       "mean_radius": round(ev["mean_radius"], 6),
                       "density": round(ev["density"], 6),
                       "parse_error": perr, "completion_tokens": ctoks,
                       "wall_s": round(wall, 2), "reconstructed": False,
                       "circles": ([[round(x, 6), round(y, 6), round(r, 6)]
                                    for (x, y, r) in circles]
                                   if circles is not None else None),
                       "raw": (None if circles is not None
                               else (text or "")[:3000])}
                append_jsonl(CAND_LOG, row)
                if ev["valid"] and ev["score"] > st["best_score"]:
                    st["best_score"] = ev["score"]
                    st["best_circles"] = [list(c) for c in circles]
                st["gen"] = gen + 1
                save_state(st)
                print(f"[{quant}] seed {s} gen {gen}: score={ev['score']:.6f} "
                      f"viable={ev['viable']} valid={ev['valid']} "
                      f"best={st['best_score']:.6f} ({wall:.0f}s)")

        # Must-differ mechanism probes: single-shot, baseline parent, explicit
        # differ demand. Echo classification happens offline (coordinates logged).
        base = baseline_packing()
        base_score = evaluate([tuple(c) for c in base])["score"]
        for k in range(md_done, MUSTDIFFER_PER_PRECISION):
            prompt = must_differ_prompt([tuple(c) for c in base], base_score)
            text, gerr, ctoks, wall = generate(llm, prompt, 990000 + k)
            circles, perr = parse_proposal(text) if gerr is None else (None, gerr)
            ev = evaluate(circles)
            append_jsonl(MUSTDIFFER_LOG, {
                "kind": "must_differ_probe", "quant": quant, "probe": k,
                "parent_score": round(base_score, 6),
                "score": round(ev["score"], 6), "viable": ev["viable"],
                "valid": ev["valid"], "n_circles": ev["n"], "parse_error": perr,
                "completion_tokens": ctoks, "wall_s": round(wall, 2),
                "reconstructed": False,
                "circles": ([[round(x, 6), round(y, 6), round(r, 6)]
                             for (x, y, r) in circles]
                            if circles is not None else None),
                "raw": (None if circles is not None else (text or "")[:3000])})
            print(f"[{quant}] must-differ {k}: score={ev['score']:.6f} "
                  f"viable={ev['viable']} valid={ev['valid']}")
    finally:
        del llm
        gc.collect()
        try:
            os.remove(path)
            print(f"[cleanup] removed {fname}")
        except OSError:
            pass
    snapshot_zip()


def summarize():
    rows = [json.loads(l) for l in open(CAND_LOG)] if os.path.exists(CAND_LOG) else []
    md = [json.loads(l) for l in open(MUSTDIFFER_LOG)] if os.path.exists(MUSTDIFFER_LOG) else []
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
        qm = [p for p in md if p["quant"] == quant]
        out[quant] = {
            "per_seed": per, "mean_best": round(mean, 6),
            "pop_std_best": round(math.sqrt(
                sum((b - mean) ** 2 for b in bests) / len(bests)), 6),
            "viability": f"{sum(1 for r in qr if r['viable'])}/{len(qr)}",
            "validity": f"{sum(1 for r in qr if r['valid'])}/{len(qr)}",
            "mustdiffer_n": len(qm),
            "mustdiffer_valid": sum(1 for p in qm if p["valid"]),
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
        summarize()
    snapshot_zip()
    print("\n[done] IQ2 algorithm-control sweep complete.")


if __name__ == "__main__":
    main()
