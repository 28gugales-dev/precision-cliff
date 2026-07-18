#!/usr/bin/env python
"""Stats for the 14B IQ2 ALGORITHM CONTROL run
(kernel sohamgugalet/precision-sweep-14b-iq2).

Reads candidates_precision_14b_iq2.jsonl and mustdiffer_14b_iq2.jsonl and
computes, per quant (q2_k_imx = bartowski imatrix Q2_K, iq2_m = bartowski
IQ2_M):
  - viability / validity / per-seed bests (paper conventions)
  - coordinate-verified parent-echo vs the lineage's RUNNING parent
    (order-insensitive, 6 dp) — plus score_echo / score_only diagnostics
  - seed-level improvement past the seeded baseline (0.89999)
  - must-differ probes: coordinate echo vs the GIVEN static baseline parent
Registered decision-rule audit (header of kaggle_precision_sweep_14b_iq2.py):
  D1 both quants coord-echo >=60% -> cliff generalizes across 2-bit-class
     algorithms
  D2 q2_k_imx >=60% but iq2_m <=35% -> cliff tracks quantization quality,
     not raw bit-width
  D3 q2_k_imx <=35% -> original cliff at least partly specific to the
     official no-imatrix Q2_K file
  Intermediate -> inconclusive
"""

import json
import math
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    BASE, "precision_sweep_14b_iq2")
CAND = os.path.join(DATA_DIR, "candidates_precision_14b_iq2.jsonl")
MD = os.path.join(DATA_DIR, "mustdiffer_14b_iq2.jsonl")
OUT = os.path.join(BASE, "results_precision_14b_iq2.json")

QUANTS = ["q2_k_imx", "iq2_m"]
SEEDS = [2222, 3333, 5555, 7777, 9999]
BASELINE_SCORE = 0.89999
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
    return tuple(sorted(tuple(round(v, 6) for v in c) for c in circles))


def fisher_p(a, b, c, d):
    try:
        from scipy.stats import fisher_exact
        return fisher_exact([[a, b], [c, d]])[1]
    except ImportError:
        pass
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
    md = [json.loads(l) for l in open(MD)] if os.path.exists(MD) else []
    assert all(r.get("reconstructed") is False for r in rows + md), \
        "reconstructed row found"

    base_canon = canon(baseline_packing())
    out = {}
    for q in QUANTS:
        qrows = [r for r in rows if r["quant"] == q]
        per_seed = {}
        n_valid = n_coord = n_score = n_score_only = 0
        per_seed_echo = {}
        for s in SEEDS:
            lineage = sorted((r for r in qrows if r["seed"] == s),
                             key=lambda r: r["gen"])
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
            per_seed[s] = {"best": round(best, 6),
                           "improved": best > BASELINE_SCORE}
            per_seed_echo[s] = f"{se_coord}/{se_valid}"
        viable = sum(1 for r in qrows if r["viable"])
        valid = sum(1 for r in qrows if r["valid"])
        qmd = [p for p in md if p["quant"] == q]
        md_valid = [p for p in qmd if p["valid"]]
        md_echo = sum(1 for p in md_valid
                      if p["circles"] is not None
                      and canon(p["circles"]) == base_canon)
        out[q] = {
            "rows": len(qrows),
            "viability": f"{viable}/{len(qrows)}",
            "viability_ci": wilson_ci(viable, len(qrows)),
            "validity": f"{valid}/{len(qrows)}",
            "seeds_improved": sum(1 for s in SEEDS if per_seed[s]["improved"]),
            "per_seed_best": {s: per_seed[s]["best"] for s in SEEDS},
            "valid_rows": n_valid,
            "coord_echo": n_coord, "score_echo": n_score,
            "score_only_echo": n_score_only,
            "coord_echo_rate": round(n_coord / n_valid, 3) if n_valid else None,
            "per_seed_coord_echo": per_seed_echo,
            "mustdiffer_n": len(qmd),
            "mustdiffer_valid": len(md_valid),
            "mustdiffer_coord_echo": md_echo,
            "mustdiffer_echo_rate": (round(md_echo / len(md_valid), 3)
                                     if md_valid else None),
        }

    kc, kv = out["q2_k_imx"]["coord_echo"], out["q2_k_imx"]["valid_rows"]
    ic, iv = out["iq2_m"]["coord_echo"], out["iq2_m"]["valid_rows"]
    out["_tests"] = {
        "coord_echo_imx_vs_iq2m_fisher_p_DESCRIPTIVE":
            fisher_p(kc, kv - kc, ic, iv - ic),
    }
    k_rate = kc / kv if kv else None
    i_rate = ic / iv if iv else None
    if kv == 0 or iv == 0:
        verdict = "insufficient_valid_rows"
    elif k_rate >= 0.60 and i_rate >= 0.60:
        verdict = "D1_cliff_generalizes_across_2bit_algorithms"
    elif k_rate >= 0.60 and i_rate <= 0.35:
        verdict = "D2_cliff_tracks_quant_quality_not_bit_width"
    elif k_rate <= 0.35:
        verdict = "D3_original_cliff_partly_specific_to_official_q2k"
    else:
        verdict = "inconclusive_intermediate_rates"
    out["_decision"] = {"q2_k_imx_echo_rate": k_rate, "iq2_m_echo_rate": i_rate,
                        "verdict": verdict}
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
