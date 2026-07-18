#!/usr/bin/env python
"""
Verification + statistics for the Kaggle GGUF precision sweep.
Reads precision_sweep/candidates_precision.jsonl + probes_precision.jsonl,
verifies integrity (row counts, reconstructed:false, live-logged fields),
computes per-quant stats with Wilson CIs, Fisher exact tests, and circle-count
drift. Writes results_precision_local.json next to this script.
"""
import json
import math
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SWEEP = os.path.join(HERE, "precision_sweep")

QUANTS = ["fp16", "q8_0", "q4_k_m", "q3_k_m", "q2_k"]
BPW = {"fp16": 16.0, "q8_0": 8.5, "q4_k_m": 4.85, "q3_k_m": 3.91, "q2_k": 3.35}
SEEDS = [42, 123, 456, 789, 1111]
BASELINE = 0.89999
CEILING = 2.5414213562


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(100 * (c - m) / d, 1), round(100 * (c + m) / d, 1)


def fisher_exact_two_sided(a, b, c, d):
    """2x2 table [[a,b],[c,d]] two-sided Fisher exact via hypergeometric."""
    n = a + b + c + d
    row1, col1 = a + b, a + c

    def pmf(x):
        return (math.comb(col1, x) * math.comb(n - col1, row1 - x)
                / math.comb(n, row1))

    p_obs = pmf(a)
    lo = max(0, row1 + col1 - n)
    hi = min(row1, col1)
    return sum(pmf(x) for x in range(lo, hi + 1) if pmf(x) <= p_obs + 1e-12)


# ---------- integrity ---------------------------------------------------------
rows = [json.loads(l) for l in open(os.path.join(SWEEP, "candidates_precision.jsonl"), encoding="utf-8")]
probes = [json.loads(l) for l in open(os.path.join(SWEEP, "probes_precision.jsonl"), encoding="utf-8")]
prov = json.load(open(os.path.join(SWEEP, "provenance.json"), encoding="utf-8"))

problems = []
if len(rows) != 250:
    problems.append(f"expected 250 loop rows, got {len(rows)}")
if len(probes) != 30:
    problems.append(f"expected 30 probe rows, got {len(probes)}")
for r in rows + probes:
    if r.get("reconstructed") is not False:
        problems.append(f"row without reconstructed:false -> {str(r)[:80]}")
        break
per_cond = Counter((r["quant"], r["seed"]) for r in rows)
bad = {k: v for k, v in per_cond.items() if v != 10}
if bad:
    problems.append(f"conditions without exactly 10 gens: {bad}")
gen_sets = {k for k in per_cond}
expected = {(q, s) for q in QUANTS for s in SEEDS}
if gen_sets != expected:
    problems.append(f"missing conditions: {expected - gen_sets}")
dup = [k for k, v in Counter((r["quant"], r["seed"], r["gen"]) for r in rows).items() if v > 1]
if dup:
    problems.append(f"duplicate (quant,seed,gen): {dup[:5]}")

print("INTEGRITY:", "OK" if not problems else problems)
print("provenance quants:", sorted(prov.keys()) if isinstance(prov, dict) else prov)

# ---------- per-quant stats ---------------------------------------------------
out = {"integrity": problems or "OK", "per_quant": {}}
for q in QUANTS:
    qr = [r for r in rows if r["quant"] == q]
    k_v = sum(1 for r in qr if r["viable"])
    k_a = sum(1 for r in qr if r["valid"])
    bests = []
    for s in SEEDS:
        bests.append(max((r["score"] for r in qr if r["seed"] == s and r["valid"]), default=0.0))
    mean_best = sum(bests) / len(bests)
    pop_std = math.sqrt(sum((b - mean_best) ** 2 for b in bests) / len(bests))
    valid_scores = [r["score"] for r in qr if r["valid"]]
    at_baseline = sum(1 for x in valid_scores if abs(x - BASELINE) < 1e-4)
    qp = [p for p in probes if p["quant"] == q]
    out["per_quant"][q] = {
        "bpw": BPW[q],
        "viable": f"{k_v}/50", "viable_ci": wilson(k_v, 50),
        "valid": f"{k_a}/50", "valid_ci": wilson(k_a, 50),
        "mean_best": round(mean_best, 6), "pop_std_best": round(pop_std, 6),
        "per_seed_best": dict(zip(map(str, SEEDS), [round(b, 6) for b in bests])),
        "max_best": round(max(bests), 6),
        "valid_at_exact_baseline": f"{at_baseline}/{len(valid_scores)}",
        "probes_valid": f"{sum(1 for p in qp if p['valid'])}/{len(qp)}",
        "count_drift": dict(Counter(min(r["n_circles"], 99) for r in qr).most_common(8)),
    }
    o = out["per_quant"][q]
    print(f"{q:8s} bpw={BPW[q]:5.2f}  viable {o['viable']} CI{o['viable_ci']}  "
          f"valid {o['valid']} CI{o['valid_ci']}  mean_best={o['mean_best']:.4f}  "
          f"max={o['max_best']:.4f}  probes {o['probes_valid']}")

# ---------- hypothesis tests --------------------------------------------------
v = {q: sum(1 for r in rows if r["quant"] == q and r["viable"]) for q in QUANTS}
others = sum(v[q] for q in QUANTS if q != "q2_k")
tests = {
    "q2k_vs_fp16_viability": fisher_exact_two_sided(v["q2_k"], 50 - v["q2_k"], v["fp16"], 50 - v["fp16"]),
    "q2k_vs_pooled_others_viability": fisher_exact_two_sided(v["q2_k"], 50 - v["q2_k"], others, 200 - others),
    "fp16_vs_q3km_viability": fisher_exact_two_sided(v["fp16"], 50 - v["fp16"], v["q3_k_m"], 50 - v["q3_k_m"]),
}
out["fisher_two_sided_p"] = {k: round(p, 5) for k, p in tests.items()}
print("fisher:", out["fisher_two_sided_p"])

# global facts
all_valid_scores = [r["score"] for r in rows if r["valid"]]
out["global"] = {
    "total_loop_rows": len(rows), "total_probes": len(probes),
    "probes_valid_total": sum(1 for p in probes if p["valid"]),
    "best_score_anywhere": round(max(all_valid_scores), 6) if all_valid_scores else 0.0,
    "recall_ceiling": CEILING,
    "n_scores_at_canonical": sum(1 for x in all_valid_scores if abs(x - CEILING) < 1e-3),
    "n_valid_at_exact_baseline_recipe": sum(1 for x in all_valid_scores if abs(x - BASELINE) < 1e-4),
    "count_drift_all": dict(Counter(r["n_circles"] for r in rows).most_common(12)),
}
print("global:", json.dumps(out["global"], indent=1))

with open(os.path.join(HERE, "results_precision_local.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print("written results_precision_local.json")
