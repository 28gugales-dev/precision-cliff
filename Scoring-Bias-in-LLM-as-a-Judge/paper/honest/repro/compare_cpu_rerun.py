#!/usr/bin/env python
"""Compare a CPU replication of scaled_harness.py against results_scaled.json.

For every family present in both files, and every probe present in both,
reports per-checkpoint agreement of the per-item expected scores, argmax
scores, the bias delta (max minus min of variant means), and the headline
instruct effect (instruct delta minus base delta). Writes a JSON summary and
prints a table.

Usage:
  python compare_cpu_rerun.py [rerun.json] [--out results_cpu_rerun_comparison.json]
"""
import json, os, sys, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
rerun_path = next((a for a in sys.argv[1:] if not a.startswith("--")),
                  os.path.join(HERE, "results_scaled_cpu_rerun.json"))
out_path = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else \
    os.path.join(HERE, "results_cpu_rerun_comparison.json")

old = json.load(open(os.path.join(HERE, "results_scaled.json")))
new = json.load(open(rerun_path))

def delta(cell):
    means = [v["mean"] for v in cell.values()]
    return max(means) - min(means)

fams = [f for f in new["results"] if f in old["results"]
        and all(k in new["results"][f] for k in ("base", "instruct"))]
probes = [p for p in old["results"][fams[0]]["base"] if p in new["results"][fams[0]]["base"]]
new_only_probes = [p for p in new["results"][fams[0]]["base"] if p not in old["results"][fams[0]]["base"]]

item_diffs, argmax_agree, rows, effect_rows = [], [], [], []
for f in fams:
    for ck in ("base", "instruct"):
        for p in probes:
            for v in old["results"][f][ck][p]:
                a = new["results"][f][ck][p][v]["per_item"]
                b = old["results"][f][ck][p][v]["per_item"]
                item_diffs += [abs(x - y) for x, y in zip(a, b)]
                aa = new["results"][f][ck][p][v]["per_item_argmax"]
                bb = old["results"][f][ck][p][v]["per_item_argmax"]
                argmax_agree += [x == y for x, y in zip(aa, bb)]
    for p in probes:
        dn = {ck: delta(new["results"][f][ck][p]) for ck in ("base", "instruct")}
        do = {ck: delta(old["results"][f][ck][p]) for ck in ("base", "instruct")}
        en, eo = dn["instruct"] - dn["base"], do["instruct"] - do["base"]
        rows.append({"family": f, "probe": p,
                     "delta_base_new": round(dn["base"], 4), "delta_base_old": round(do["base"], 4),
                     "delta_inst_new": round(dn["instruct"], 4), "delta_inst_old": round(do["instruct"], 4),
                     "effect_new": round(en, 4), "effect_old": round(eo, 4),
                     "effect_sign_agree": (en > 0) == (eo > 0)})

# panel-level headline: mean instruct effect per probe, old vs new, on the shared families
per_probe = {}
for p in probes:
    en = [r["effect_new"] for r in rows if r["probe"] == p]
    eo = [r["effect_old"] for r in rows if r["probe"] == p]
    per_probe[p] = {"mean_effect_new": round(st.mean(en), 4), "mean_effect_old": round(st.mean(eo), 4),
                    "families_positive_new": sum(e > 0 for e in en),
                    "families_positive_old": sum(e > 0 for e in eo), "n": len(en)}

summary = {
    "rerun_file": os.path.basename(rerun_path),
    "rerun_env": new.get("env"), "rerun_dtype": new.get("dtype"),
    "n_families_compared": len(fams), "families": fams,
    "probes_compared": probes, "probes_new_only": new_only_probes,
    "per_item_abs_diff": {"n": len(item_diffs), "mean": round(st.mean(item_diffs), 5),
                          "median": round(st.median(item_diffs), 5), "p95": round(sorted(item_diffs)[int(0.95 * len(item_diffs))], 5),
                          "max": round(max(item_diffs), 5)},
    "argmax_agreement": round(sum(argmax_agree) / len(argmax_agree), 5),
    "delta_abs_diff": {"mean": round(st.mean(abs(r["delta_base_new"] - r["delta_base_old"]) for r in rows) , 5),
                       "max": round(max(max(abs(r["delta_base_new"] - r["delta_base_old"]),
                                          abs(r["delta_inst_new"] - r["delta_inst_old"])) for r in rows), 5)},
    "effect_sign_agreement": round(sum(r["effect_sign_agree"] for r in rows) / len(rows), 5),
    "per_probe_headline": per_probe, "cells": rows,
}
with open(out_path, "w") as fh:
    json.dump(summary, fh, indent=2)

print(f"families compared: {len(fams)}  probes: {probes}  new-only probes: {new_only_probes}")
d = summary["per_item_abs_diff"]
print(f"per-item |exp diff| over {d['n']} cells: mean {d['mean']:.4f}  median {d['median']:.4f}  p95 {d['p95']:.4f}  max {d['max']:.4f}")
print(f"argmax agreement: {summary['argmax_agreement']:.4f}   delta |diff| mean {summary['delta_abs_diff']['mean']:.4f} max {summary['delta_abs_diff']['max']:.4f}")
print(f"instruct-effect sign agreement: {summary['effect_sign_agreement']:.3f} over {len(rows)} family x probe cells")
print(f"\n{'probe':18s} {'mean effect new':>16s} {'old':>8s}   {'families +':>12s}")
for p, s in per_probe.items():
    print(f"{p:18s} {s['mean_effect_new']:>16.3f} {s['mean_effect_old']:>8.3f}   {s['families_positive_new']:>2d}/{s['n']} vs {s['families_positive_old']:>2d}/{s['n']}")
worst = sorted(rows, key=lambda r: -abs(r["effect_new"] - r["effect_old"]))[:3]
print("\nlargest effect disagreements:")
for r in worst:
    print(f"  {r['family']:16s} {r['probe']:17s} effect new {r['effect_new']:+.3f} old {r['effect_old']:+.3f}")
print("\nwrote", out_path)
