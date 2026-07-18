#!/usr/bin/env python
"""
Classical comparator at matched budget (review concern: no non-LLM baseline).

Calibrates what "weak but real search" achieves on the N=26 circle-packing
objective under EXACTLY the loop arms' budget: 5 seeds x 10 proposals each
(50 evaluations per condition), seeded from the same 0.9-score grid baseline,
elitist state tracking identical to Arms A-E.

Conditions (2 proposal families x 2 acceptance rules):
  raw_greedy    jitter (x,y,r) of 3 random circles, sigma=0.005, NO repair;
                accept if valid and better. Mirrors the LLM's contract:
                proposals are full coordinate lists, validity checked after.
  raw_sa        same moves, Metropolis acceptance (T: 0.02 -> 0.002 geometric);
                elitist best still tracked separately.
  repair_greedy jitter centers of 3 random circles, sigma=0.02, then assign
                radii by the max-radius decoder (iterative sweep to the
                feasible fixed point); accept if better.
  repair_sa     same moves, Metropolis acceptance.

The decoder is a strong local repair; its zero-perturbation value from the
seeded grid is reported separately (decoder_floor) so search gains beyond
repair are not conflated with the repair itself.

Extended reference (disclosed as NOT budget-matched): repair_sa continued to
5,000 evaluations per seed, to place the loop's converged value on the
classical compute curve.

Zero LLM involvement. Deterministic under seed. Every evaluation logged live
to candidates_classical.jsonl (reconstructed:false).
"""
import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
CAND_LOG = os.path.join(HERE, "candidates_classical.jsonl")
RESULTS = os.path.join(HERE, "results_classical.json")

N = 26
EPS = 1e-6
SEEDS = [42, 123, 456, 789, 1111]   # same seed values as Arms A-D
GENS = 10                            # matched budget: 10 evals per lineage
EXTENDED_EVALS = 5000
MARGIN = 1e-6                        # feasibility margin inside decoder


def baseline_packing():
    r = round(0.9 / N, 6)
    pts = []
    for row in range(5):
        for col in range(6):
            if len(pts) >= N:
                break
            pts.append((round((col + 0.5) / 6.0, 6), round((row + 0.5) / 5.0, 6), r))
    return pts


def evaluate(circles):
    res = {"viable": False, "valid": False, "score": 0.0,
           "n": 0 if circles is None else len(circles)}
    if circles is None:
        return res
    if len(circles) != N or any(r <= 0 for (_, _, r) in circles):
        return res
    res["viable"] = True
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
        res["score"] = sum(r for (_, _, r) in circles)
    return res


# ------------------------------ proposal moves -------------------------------

def move_raw(circles, rng, k=3, sigma=0.005):
    """Jitter x, y, r of k random circles. No repair — validity is the
    proposal's own problem, as it is for the LLM proposer."""
    out = list(circles)
    for i in rng.sample(range(N), k):
        x, y, r = out[i]
        out[i] = (x + rng.gauss(0, sigma), y + rng.gauss(0, sigma),
                  max(1e-4, r + rng.gauss(0, sigma)))
    return out


def decode_radii(centers):
    """Max-radius decoder: start from the guaranteed-feasible half-min-distance
    assignment, then sweep r_i toward cap = min(wall, min_j (d_ij - r_j)),
    growing or shrinking, until a feasible fixed point."""
    d = [[math.hypot(centers[i][0] - centers[j][0],
                     centers[i][1] - centers[j][1])
          for j in range(N)] for i in range(N)]
    wall = [min(x, 1 - x, y, 1 - y) for (x, y) in centers]
    rs = [max(1e-6, min(wall[i],
                        min(d[i][j] / 2 for j in range(N) if j != i)) - MARGIN)
          for i in range(N)]
    for _ in range(60):
        changed = False
        for i in range(N):
            cap = min(wall[i],
                      min(d[i][j] - rs[j] for j in range(N) if j != i)) - MARGIN
            cap = max(cap, 1e-6)
            if abs(cap - rs[i]) > 1e-12:
                rs[i] = cap
                changed = True
        if not changed:
            break
    return rs


def move_repair(circles, rng, k=3, sigma=0.02):
    """Jitter centers of k random circles, clamp into the square, re-derive
    every radius with the max-radius decoder."""
    centers = [(x, y) for (x, y, _) in circles]
    for i in rng.sample(range(N), k):
        x, y = centers[i]
        centers[i] = (min(1 - 1e-4, max(1e-4, x + rng.gauss(0, sigma))),
                      min(1 - 1e-4, max(1e-4, y + rng.gauss(0, sigma))))
    rs = decode_radii(centers)
    return [(cx, cy, r) for ((cx, cy), r) in zip(centers, rs)]


# ------------------------------ acceptance -----------------------------------

def run_lineage(cond, seed, gens, log=True):
    """One elitist lineage, budget = gens evaluations. Returns final best."""
    rng = random.Random(seed)
    family, accept = cond.split("_")
    move = move_raw if family == "raw" else move_repair
    cur = baseline_packing()
    cur_score = evaluate(cur)["score"]
    best, best_score = list(cur), cur_score
    t0, t1 = 0.02, 0.002
    for gen in range(gens):
        prop = move(cur, rng)
        ev = evaluate(prop)
        temp = t0 * (t1 / t0) ** (gen / max(1, gens - 1))
        accepted = False
        if ev["valid"]:
            if ev["score"] > cur_score:
                accepted = True
            elif accept == "sa":
                accepted = rng.random() < math.exp((ev["score"] - cur_score) / temp)
        if accepted:
            cur, cur_score = prop, ev["score"]
            if cur_score > best_score:
                best, best_score = list(cur), cur_score
        if log:
            row = {"arm": "classical_baseline", "proposer": cond,
                   "seed": seed, "gen": gen,
                   "parent_score": round(cur_score if not accepted else 0, 6),
                   "score": round(ev["score"], 6), "viable": ev["viable"],
                   "valid": ev["valid"], "accepted": accepted,
                   "best_so_far": round(best_score, 6),
                   "reconstructed": False,
                   "circles": ([[round(x, 6), round(y, 6), round(r, 6)]
                                for (x, y, r) in prop] if ev["valid"] else None)}
            with open(CAND_LOG, "a") as f:
                f.write(json.dumps(row) + "\n")
    return best_score


def self_test():
    base = baseline_packing()
    ev = evaluate(base)
    assert ev["valid"] and abs(ev["score"] - 0.89999) < 1e-4
    rs = decode_radii([(x, y) for (x, y, _) in base])
    decoded = [(x, y, r) for ((x, y, _), r) in zip(base, rs)]
    dev = evaluate(decoded)
    assert dev["valid"], "decoder output must be valid"
    assert dev["score"] > ev["score"], "decoder must expand the seeded grid"
    print(f"[selftest] OK; decoder floor from seeded grid = {dev['score']:.6f}")
    return dev["score"]


def main():
    if os.path.exists(CAND_LOG):
        os.remove(CAND_LOG)
    decoder_floor = self_test()
    conds = ["raw_greedy", "raw_sa", "repair_greedy", "repair_sa"]
    out = {"decoder_floor_from_seeded_grid": round(decoder_floor, 6),
           "matched_budget": {}, "extended": {}}
    for cond in conds:
        bests = [run_lineage(cond, s, GENS) for s in SEEDS]
        mean = sum(bests) / len(bests)
        out["matched_budget"][cond] = {
            "per_seed_best": [round(b, 6) for b in bests],
            "mean_best": round(mean, 6),
            "pop_std_best": round(math.sqrt(
                sum((b - mean) ** 2 for b in bests) / len(bests)), 6)}
        print(f"[matched 50-eval] {cond}: mean {mean:.6f} "
              f"per-seed {[round(b, 4) for b in bests]}")
    ext = [run_lineage("repair_sa", 900000 + s, EXTENDED_EVALS, log=False)
           for s in SEEDS]
    emean = sum(ext) / len(ext)
    out["extended"]["repair_sa_5000"] = {
        "per_seed_best": [round(b, 6) for b in ext],
        "mean_best": round(emean, 6),
        "evals_per_seed": EXTENDED_EVALS,
        "note": "NOT budget-matched; classical compute-curve reference only"}
    print(f"[extended 5000-eval] repair_sa: mean {emean:.6f} "
          f"per-seed {[round(b, 4) for b in ext]}")
    with open(RESULTS, "w") as f:
        json.dump(out, f, indent=2)
    print("[done] results ->", RESULTS)


if __name__ == "__main__":
    main()
