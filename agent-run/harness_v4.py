#!/usr/bin/env python
"""
Arm E harness — N-generality arm (N=23 and N=27), Claude Haiku proposer.

Tests whether the constructible-attractor behaviour observed at N=26 (five-seed
convergence onto the 5x5-grid-plus-filler packing, 2.541421) is specific to
N=26 or a general property of the template family. Same single-lineage elitist
protocol as Arms A-D and the precision sweeps: proposer is a fresh, memoryless
LLM invocation per generation; all scoring deterministic here; every candidate
logged live (reconstructed:false) WITH coordinates.

INTERNAL DIRECTIONAL HYPOTHESES (written before any proposal was sampled;
local-file prereg only — timestamped by the public repo's first commit):
  H1 N=27 (template fits: 5x5 grid + 2 fillers analogous to N=26's +1):
     low inter-seed variance; seeds converge onto the grid+filler family.
  H2 N=23 (template misfits: 23 < 25, the clean 5x5 grid overshoots the
     count): higher inter-seed variance and/or convergence to a different
     construction — Arm-C-like dispersion predicts variance returns when the
     template does not fit cleanly.
  Both informative; neither triggers withdrawal of anything.

Commands:
  initall                  init state for both N x 5 seeds, clear nothing
  prompts                  print JSON {key: prompt} for every lineage at its
                           current gen (key = "n<N>_seed<S>_gen<G>")
  batchstep <gen>          step every lineage at <gen>, reading
                           prop_v4/n<N>_seed<S>_gen_<gen>.txt
  summary                  recompute results_v4.json

Proposal files are the RAW final text of one Claude Haiku subagent invocation
(no tools allowed by prompt); missing/garbage files count as viability
failures — real data, never reconstructed.
"""
import ast
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(HERE, "state_v4")
PROP_DIR = os.path.join(HERE, "prop_v4")
CAND_LOG = os.path.join(HERE, "candidates_v4.jsonl")
RESULTS = os.path.join(HERE, "results_v4.json")

NS = [23, 27]
SEEDS = [42, 123, 456, 789, 1111]
GENS = 10
EPS = 1e-6


def baseline_packing(n):
    """First n cells of the 6-wide grid used by every other arm; r = 0.9/n so
    the baseline score is 0.9 at every N (comparable seeded start)."""
    r = round(0.9 / n, 6)
    pts = []
    for row in range(5):
        for col in range(6):
            if len(pts) >= n:
                break
            pts.append([round((col + 0.5) / 6.0, 6), round((row + 0.5) / 5.0, 6), r])
    return pts


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


def evaluate(circles, n):
    res = {"viable": False, "valid": False, "score": 0.0,
           "mean_radius": 0.0, "density": 0.0,
           "n": 0 if circles is None else len(circles)}
    if circles is None:
        return res
    if len(circles) != n or any(r <= 0 for (_, _, r) in circles):
        return res
    res["viable"] = True
    radii = [r for (_, _, r) in circles]
    res["mean_radius"] = sum(radii) / n
    res["density"] = sum(math.pi * r * r for r in radii)
    inside = all(x - r >= -EPS and x + r <= 1 + EPS and
                 y - r >= -EPS and y + r <= 1 + EPS for (x, y, r) in circles)
    overlap = False
    for i in range(n):
        xi, yi, ri = circles[i]
        for j in range(i + 1, n):
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


def loop_prompt(n, best_circles, best_score):
    """Arm B's fixed prompt (no target value, no return-parent clause), with N
    parameterized and an explicit no-tools rule for agentic proposers."""
    packing = json.dumps([[round(x, 6), round(y, 6), round(r, 6)]
                          for (x, y, r) in best_circles])
    return (
        "You are the proposal step of an evolutionary search for circle packings.\n"
        f"Current best packing (sum of radii = {best_score:.6f}):\n{packing}\n\n"
        f"Produce a packing of exactly {n} circles with a HIGHER sum of radii.\n"
        f"MUST hold: exactly {n} circles; every circle fully inside the unit square "
        "[0,1]x[0,1] (x-r >= 0, x+r <= 1, same for y); no two circles overlap "
        "(distance between centers >= sum of the two radii; touching is allowed).\n"
        "Do not write or execute code — construct the packing by reasoning "
        "alone.\n"
        f"Output ONLY the raw Python list of {n} [x, y, r] lists. No explanation, "
        "no code fences, no other text."
    )


def self_test():
    for n in NS:
        base = baseline_packing(n)
        assert len(base) == n
        ev = evaluate([tuple(c) for c in base], n)
        assert ev["valid"], f"baseline N={n} must be valid"
        assert abs(ev["score"] - 0.9) < 1e-4, f"baseline score {ev['score']}"
        bad = [tuple(c) for c in base]
        bad[0] = (bad[0][0], bad[0][1], 0.5)
        assert not evaluate(bad, n)["valid"]
    c, err = parse_proposal("junk [[0.1, 0.1, 0.05]] junk")
    assert err is None and len(c) == 1
    print("[selftest] v4 evaluator/parser OK for N=23,27")


# ---------- state ----------

def spath(n, seed):
    return os.path.join(STATE_DIR, f"n{n}_seed_{seed}.json")


def load_state(n, seed):
    with open(spath(n, seed)) as f:
        return json.load(f)


def save_state(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(spath(st["n"], st["seed"]), "w") as f:
        json.dump(st, f)


def cmd_initall():
    self_test()
    os.makedirs(PROP_DIR, exist_ok=True)
    made = 0
    for n in NS:
        for s in SEEDS:
            if os.path.exists(spath(n, s)):
                continue  # never clobber a live lineage
            base = baseline_packing(n)
            ev = evaluate([tuple(c) for c in base], n)
            save_state({"n": n, "seed": s, "gen": 0,
                        "best_circles": base, "best_score": ev["score"]})
            made += 1
    print(f"[init] {made} lineages initialized (existing preserved)")


def cmd_prompts():
    out = {}
    for n in NS:
        for s in SEEDS:
            st = load_state(n, s)
            if st["gen"] >= GENS:
                continue
            key = f"n{n}_seed{s}_gen{st['gen']}"
            out[key] = loop_prompt(n, [tuple(c) for c in st["best_circles"]],
                                   st["best_score"])
    print(json.dumps(out))


def cmd_batchstep(gen):
    for n in NS:
        for s in SEEDS:
            st = load_state(n, s)
            if st["gen"] != gen:
                print(f"n{n} seed {s}: SKIP (state at gen {st['gen']})")
                continue
            pf = os.path.join(PROP_DIR, f"n{n}_seed{s}_gen_{gen}.txt")
            raw = None
            if os.path.exists(pf):
                with open(pf, encoding="utf-8", errors="replace") as f:
                    raw = f.read()
            t0 = time.time()
            circles, perr = parse_proposal(raw)
            ev = evaluate(circles, n)
            row = {"arm": "n_generality", "proposer": "claude-haiku",
                   "n_target": n, "seed": s, "gen": gen,
                   "parent_score": round(st["best_score"], 6),
                   "score": round(ev["score"], 6), "viable": ev["viable"],
                   "valid": ev["valid"], "n_circles": ev["n"],
                   "mean_radius": round(ev["mean_radius"], 6),
                   "density": round(ev["density"], 6), "parse_error": perr,
                   "wall_s": round(time.time() - t0, 4), "reconstructed": False,
                   "circles": ([[round(x, 6), round(y, 6), round(r, 6)]
                                for (x, y, r) in circles]
                               if circles is not None else None),
                   "raw": (None if circles is not None else (raw or "")[:3000])}
            with open(CAND_LOG, "a") as f:
                f.write(json.dumps(row) + "\n")
                f.flush()
                os.fsync(f.fileno())
            if ev["valid"] and ev["score"] > st["best_score"]:
                st["best_score"] = ev["score"]
                st["best_circles"] = [list(c) for c in circles]
            st["gen"] = gen + 1
            save_state(st)
            print(f"n{n} seed {s} gen {gen}: score={ev['score']:.6f} "
                  f"viable={ev['viable']} valid={ev['valid']} "
                  f"best={st['best_score']:.6f}")


def cmd_summary():
    rows = [json.loads(l) for l in open(CAND_LOG)] if os.path.exists(CAND_LOG) else []
    out = {}
    for n in NS:
        nr = [r for r in rows if r["n_target"] == n]
        if not nr:
            continue
        per = []
        for s in SEEDS:
            sr = [r for r in nr if r["seed"] == s]
            best = max((r["score"] for r in sr if r["valid"]), default=0.0)
            per.append({"seed": s, "best": round(best, 6), "gens": len(sr),
                        "viable": sum(1 for r in sr if r["viable"]),
                        "valid": sum(1 for r in sr if r["valid"])})
        bests = [p["best"] for p in per]
        mean = sum(bests) / len(bests)
        out[f"n{n}"] = {
            "per_seed": per, "mean_best": round(mean, 6),
            "pop_std_best": round(math.sqrt(
                sum((b - mean) ** 2 for b in bests) / len(bests)), 6),
            "viability": f"{sum(1 for r in nr if r['viable'])}/{len(nr)}",
            "validity": f"{sum(1 for r in nr if r['valid'])}/{len(nr)}",
        }
    with open(RESULTS, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "initall":
        cmd_initall()
    elif cmd == "prompts":
        cmd_prompts()
    elif cmd == "batchstep":
        cmd_batchstep(int(sys.argv[2]))
    elif cmd == "summary":
        cmd_summary()
    else:
        print("usage: harness_v4.py initall | prompts | batchstep <gen> | summary",
              file=sys.stderr)
        sys.exit(1)
