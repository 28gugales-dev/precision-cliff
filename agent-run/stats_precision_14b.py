#!/usr/bin/env python
"""
Stats for the 14B precision sweep, recomputed from the verbatim console log
(precision_sweep_14b_console.log — see precision_sweep_14b_README.md for why
the jsonl is unavailable). Writes results_precision_14b_local.json.
"""
import json
import math
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "precision_sweep_14b_console.log")

QUANTS = ["q8_0", "q4_k_m", "q3_k_m", "q2_k"]
BPW = {"q8_0": 8.5, "q4_k_m": 4.85, "q3_k_m": 3.91, "q2_k": 3.35}
SEEDS = [42, 123, 456, 789, 1111]
BASELINE = 0.89999

ROW = re.compile(r"\[(\w+)\] seed (\d+) gen (\d+): score=([\d.]+) "
                 r"viable=(True|False) valid=(True|False) best=([\d.]+)")
PROBE = re.compile(r"\[(\w+)\] probe (\d+): score=([\d.]+) valid=(True|False)")


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(100 * (c - m) / d, 1), round(100 * (c + m) / d, 1)


def fisher_exact_two_sided(a, b, c, d):
    n = a + b + c + d
    row1, col1 = a + b, a + c

    def pmf(x):
        return (math.comb(col1, x) * math.comb(n - col1, row1 - x)
                / math.comb(n, row1))

    p_obs = pmf(a)
    lo, hi = max(0, row1 + col1 - n), min(row1, col1)
    return sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p_obs + 1e-12)


rows, probes = [], []
for line in open(LOG, encoding="utf-8"):
    m = ROW.search(line)
    if m:
        rows.append({"quant": m.group(1), "seed": int(m.group(2)),
                     "gen": int(m.group(3)), "score": float(m.group(4)),
                     "viable": m.group(5) == "True", "valid": m.group(6) == "True",
                     "best": float(m.group(7))})
        continue
    m = PROBE.search(line)
    if m:
        probes.append({"quant": m.group(1), "probe": int(m.group(2)),
                       "score": float(m.group(3)), "valid": m.group(4) == "True"})

assert len(rows) == 200, f"expected 200 loop rows, parsed {len(rows)}"
assert len(probes) == 24, f"expected 24 probe rows, parsed {len(probes)}"
dup = [k for k, v in Counter((r["quant"], r["seed"], r["gen"]) for r in rows).items() if v > 1]
assert not dup, f"duplicate rows: {dup[:3]}"
print(f"parsed {len(rows)} loop rows + {len(probes)} probes, no duplicates")

# Parent score for each row: the seed's running best AFTER the previous gen
# (gen 0's parent is the seeded baseline). Parent-echo = valid row whose score
# equals its actual parent's score (score-inferred; coordinates unavailable).
# NOTE: an earlier version of this script compared against the hardcoded
# BASELINE only, undercounting echoes of later parents on the upper rungs
# (caught in review 2026-07-18; corrected here).
for r in rows:
    if r["gen"] == 0:
        r["parent"] = BASELINE
    else:
        prev = next(p for p in rows if p["quant"] == r["quant"]
                    and p["seed"] == r["seed"] and p["gen"] == r["gen"] - 1)
        r["parent"] = prev["best"]
    r["parent_echo"] = r["valid"] and abs(r["score"] - r["parent"]) < 1e-6

out = {"source": "precision_sweep_14b_console.log (verbatim console log; jsonl lost, see README)",
       "per_quant": {}}
for q in QUANTS:
    qr = [r for r in rows if r["quant"] == q]
    k_v = sum(1 for r in qr if r["viable"])
    k_a = sum(1 for r in qr if r["valid"])
    bests, improved, echo = [], 0, 0
    for s in SEEDS:
        b = max((r["score"] for r in qr if r["seed"] == s and r["valid"]), default=0.0)
        bests.append(b)
        if b > BASELINE + 1e-6:
            improved += 1
    echo = sum(1 for r in qr if r["valid"] and abs(r["score"] - BASELINE) < 1e-6)
    pecho = sum(1 for r in qr if r["parent_echo"])
    mean = sum(bests) / len(bests)
    std = math.sqrt(sum((x - mean) ** 2 for x in bests) / len(bests))
    out["per_quant"][q] = {
        "bpw": BPW[q],
        "viable": f"{k_v}/50", "viable_ci": wilson(k_v, 50),
        "valid": f"{k_a}/50", "valid_ci": wilson(k_a, 50),
        "mean_best": round(mean, 6), "pop_std_best": round(std, 6),
        "per_seed_best": dict(zip(map(str, SEEDS), [round(b, 6) for b in bests])),
        "seeds_improved_past_baseline": f"{improved}/5",
        "valid_rows_at_exact_baseline_score": f"{echo}/{k_a}",
        "parent_echo_rows": f"{pecho}/{k_a}",
        "probes_valid": f"{sum(1 for p in probes if p['quant'] == q and p['valid'])}/6",
    }
    o = out["per_quant"][q]
    print(f"{q:8s} viable {o['viable']} CI{o['viable_ci']}  valid {o['valid']}  "
          f"mean_best={o['mean_best']:.4f}  improved {o['seeds_improved_past_baseline']}  "
          f"baseline-echo {o['valid_rows_at_exact_baseline_score']}")

# improvement cliff: q2_k vs the three higher precisions pooled (per-seed level)
p_seed = fisher_exact_two_sided(1, 4, 15, 0)
# candidate-level PARENT-echo: q2_k echo rows vs pooled others
e_q2 = sum(1 for r in rows if r["quant"] == "q2_k" and r["parent_echo"])
v_q2 = sum(1 for r in rows if r["quant"] == "q2_k" and r["valid"])
e_ot = sum(1 for r in rows if r["quant"] != "q2_k" and r["parent_echo"])
v_ot = sum(1 for r in rows if r["quant"] != "q2_k" and r["valid"])
p_echo = fisher_exact_two_sided(e_q2, v_q2 - e_q2, e_ot, v_ot - e_ot)
# legacy baseline-only echo (what the first version of this script measured)
be_q2 = sum(1 for r in rows if r["quant"] == "q2_k" and r["valid"] and abs(r["score"] - BASELINE) < 1e-6)
be_ot = sum(1 for r in rows if r["quant"] != "q2_k" and r["valid"] and abs(r["score"] - BASELINE) < 1e-6)
# 14B vs 7B viability, same four quants (7B: 6+9+7+16 = 38/200)
v14 = sum(1 for r in rows if r["viable"])
p_scale = fisher_exact_two_sided(v14, 200 - v14, 38, 200 - 38)
out["tests"] = {
    "improvement_cliff_seedlevel_q2k_1of5_vs_others_15of15_fisher_p": round(p_seed, 5),
    "parent_echo_q2k_vs_others_fisher_p": f"{p_echo:.3e}",
    "parent_echo_counts": {"q2_k": f"{e_q2}/{v_q2}", "others_pooled": f"{e_ot}/{v_ot}"},
    "legacy_baseline_only_echo_counts": {"q2_k": f"{be_q2}/{v_q2}", "others_pooled": f"{be_ot}/{v_ot}"},
    "viability_14b_vs_7b_same_quants_fisher_p": f"{p_scale:.2e}",
    "viability_totals": {"14b": f"{v14}/200", "7b": "38/200"},
}
print(json.dumps(out["tests"], indent=1))

out["probes_valid_total"] = f"{sum(1 for p in probes if p['valid'])}/24"
out["best_score_anywhere"] = max(r["score"] for r in rows if r["valid"])

with open(os.path.join(HERE, "results_precision_14b_local.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print("written results_precision_14b_local.json")
