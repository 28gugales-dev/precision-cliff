#!/usr/bin/env python
"""Stats for the 14B durable replication (kernel sohamgugalet/precision-sweep-14b-v2).

Reads candidates_precision_14b.jsonl (coordinate-logged) and computes, per quant:
  - viability / validity / per-seed bests (same conventions as stats_precision.py)
  - parent-echo THREE ways:
      coord_echo   : proposal circles == lineage's RUNNING parent circles
                     (order-insensitive, 6-decimal rounding) — the verified metric
      score_echo   : score == running parent score to 6 dp (the old inferred metric)
      score_only   : score_echo but NOT coord_echo (the overcount the old metric
                     could not see: same radius multiset, different centers)
  - seed-level improvement (best > seeded baseline 0.89999) — primary test
  - prediction check against the preregistered block in the pushed kernel:
      P1 improvement >=4/5 upper rungs, <=2/5 q2_k
      P2 coord-echo >=60% q2_k valid rows, <=35% each upper rung
      P3 viability CIs overlap (reported, not tested here)
      P4 probes ~0 valid; canonical 2.541421 never emitted
Fisher exact (candidate-level, descriptive only — pseudo-replication caveat) via
scipy if available, else exact hypergeometric fallback.
"""

import json
import math
import os
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "precision_sweep_14b")
CAND = os.path.join(DATA_DIR, "candidates_precision_14b.jsonl")
PROBE = os.path.join(DATA_DIR, "probes_precision_14b.jsonl")
OUT = os.path.join(BASE, "results_precision_14b_v2.json")

QUANTS = ["q8_0", "q4_k_m", "q3_k_m", "q2_k"]
SEEDS = [42, 123, 456, 789, 1111]
BASELINE_SCORE = 0.89999
CANONICAL = 2.541421
N = 26


def baseline_packing():
    r = round(0.9 / N, 6)
    pts = []
    for row in range(5):
        for col in range(6):
            if len(pts) >= N:
                break
            pts.append([round((col + 0.5) / 6.0, 6), round((row + 0.5) / 5.0, 6), r])
    return pts


def canon(circles):
    """Order-insensitive canonical form, 6-dp rounding."""
    return tuple(sorted(tuple(round(v, 6) for v in c) for c in circles))


def fisher_p(a, b, c, d):
    """Two-sided Fisher exact for [[a,b],[c,d]]."""
    try:
        from scipy.stats import fisher_exact
        return fisher_exact([[a, b], [c, d]])[1]
    except ImportError:
        pass
    # exact enumeration fallback
    def logC(n, k):
        return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    r1, r2, c1 = a + b, c + d, a + c
    n = r1 + r2
    logden = logC(n, c1)
    def pt(x):
        return math.exp(logC(r1, x) + logC(r2, c1 - x) - logden)
    p_obs = pt(a)
    total = 0.0
    for x in range(max(0, c1 - r2), min(r1, c1) + 1):
        px = pt(x)
        if px <= p_obs * (1 + 1e-9):
            total += px
    return min(1.0, total)


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (round(100 * (ctr - hw), 1), round(100 * (ctr + hw), 1))


def main():
    rows = [json.loads(l) for l in open(CAND)]
    probes = [json.loads(l) for l in open(PROBE)] if os.path.exists(PROBE) else []
    assert all(r.get("reconstructed") is False for r in rows), "reconstructed row found"

    # replay lineages to attach running-parent circles to every row
    out = {}
    canonical_hits = 0
    for q in QUANTS:
        qrows = [r for r in rows if r["quant"] == q]
        per_seed = {}
        # echo counters over VALID rows
        n_valid = n_coord = n_score = n_score_only = 0
        per_seed_echo = {}
        for s in SEEDS:
            lineage = sorted((r for r in qrows if r["seed"] == s), key=lambda r: r["gen"])
            parent_circles = baseline_packing()
            parent_score = BASELINE_SCORE
            best = 0.0
            se_valid = se_coord = 0
            for r in lineage:
                assert abs(r["parent_score"] - round(parent_score, 6)) < 1e-6, \
                    f"parent mismatch {q} seed {s} gen {r['gen']}"
                if r["valid"]:
                    n_valid += 1
                    se_valid += 1
                    ce = (r["circles"] is not None
                          and canon(r["circles"]) == canon(parent_circles))
                    se_ = abs(r["score"] - round(parent_score, 6)) < 1e-6
                    n_coord += ce
                    n_score += se_
                    n_score_only += (se_ and not ce)
                    se_coord += ce
                    best = max(best, r["score"])
                    if r["score"] > parent_score:
                        parent_score = r["score"]
                        parent_circles = r["circles"]
                if abs(r["score"] - CANONICAL) < 1e-6:
                    canonical_hits += 1
            per_seed[s] = {"best": round(best, 6), "improved": best > BASELINE_SCORE,
                           "valid": se_valid, "coord_echo": se_coord}
            per_seed_echo[s] = f"{se_coord}/{se_valid}"
        viable = sum(1 for r in qrows if r["viable"])
        valid = sum(1 for r in qrows if r["valid"])
        out[q] = {
            "rows": len(qrows),
            "viability": f"{viable}/{len(qrows)}", "viability_ci": wilson_ci(viable, len(qrows)),
            "validity": f"{valid}/{len(qrows)}",
            "seeds_improved": sum(1 for s in SEEDS if per_seed[s]["improved"]),
            "per_seed_best": {s: per_seed[s]["best"] for s in SEEDS},
            "valid_rows": n_valid,
            "coord_echo": n_coord, "score_echo": n_score,
            "score_only_echo": n_score_only,
            "coord_echo_rate": round(n_coord / n_valid, 3) if n_valid else None,
            "per_seed_coord_echo": per_seed_echo,
            "probes_valid": sum(1 for p in probes if p["quant"] == q and p["valid"]),
            "probes_n": sum(1 for p in probes if p["quant"] == q),
        }

    upper = ["q8_0", "q4_k_m", "q3_k_m"]
    uc = sum(out[q]["coord_echo"] for q in upper)
    uv = sum(out[q]["valid_rows"] for q in upper)
    qc, qv = out["q2_k"]["coord_echo"], out["q2_k"]["valid_rows"]
    out["_tests"] = {
        "coord_echo_q2k_vs_upper_fisher_p_DESCRIPTIVE":
            fisher_p(qc, qv - qc, uc, uv - uc),
        "improvement_seed_level": {
            "upper_improved": [out[q]["seeds_improved"] for q in upper],
            "q2_k_improved": out["q2_k"]["seeds_improved"],
            "fisher_p_15v5_pooled": fisher_p(
                sum(out[q]["seeds_improved"] for q in upper),
                15 - sum(out[q]["seeds_improved"] for q in upper),
                out["q2_k"]["seeds_improved"], 5 - out["q2_k"]["seeds_improved"]),
        },
        "canonical_emissions": canonical_hits,
    }
    out["_predictions"] = {
        "P1_upper_improve_ge4of5": all(out[q]["seeds_improved"] >= 4 for q in upper),
        "P1_q2k_improve_le2of5": out["q2_k"]["seeds_improved"] <= 2,
        "P2_q2k_coord_echo_ge60pct": (qv > 0 and qc / qv >= 0.60),
        "P2_upper_coord_echo_le35pct_each": all(
            out[q]["valid_rows"] == 0 or out[q]["coord_echo"] / out[q]["valid_rows"] <= 0.35
            for q in upper),
        "P4_probes_valid_total": sum(out[q]["probes_valid"] for q in QUANTS),
        "P4_canonical_never": canonical_hits == 0,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
