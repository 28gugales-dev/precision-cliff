#!/usr/bin/env python
"""Arm D stats + fig4. Reads candidates_v3.jsonl (live log) only."""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "candidates_v3.jsonl"))]
SEEDS = [42, 123, 456, 789, 1111]


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


bests, climbs_total, traj = [], 0, {}
for s in SEEDS:
    rs = sorted([r for r in rows if r["seed"] == s], key=lambda r: r["gen"])
    best, climbs, first = 0.0, 0, True
    series = []
    for r in rs:
        if r["valid"] and r["score"] > best:
            if not first:
                climbs += 1
            first = False
            best = r["score"]
        series.append(best)
    bests.append(best)
    climbs_total += climbs
    traj[s] = series
    print(f"seed {s}: best={best:.6f} climbs_after_first_valid={climbs}")

n = len(bests)
mean = sum(bests) / n
sd = math.sqrt(sum((b - mean) ** 2 for b in bests) / (n - 1))
viable = sum(1 for r in rows if r["viable"])
valid = sum(1 for r in rows if r["valid"])
vlo, vhi = wilson(viable, len(rows))
glo, ghi = wilson(valid, len(rows))
errs = {}
for r in rows:
    if r["exec_error"]:
        errs[r["exec_error"]] = errs.get(r["exec_error"], 0) + 1
print(f"\nmean_best={mean:.6f} sd={sd:.6f} n_rows={len(rows)}")
print(f"viable {viable}/{len(rows)} CI [{vlo*100:.1f}, {vhi*100:.1f}]")
print(f"valid  {valid}/{len(rows)} CI [{glo*100:.1f}, {ghi*100:.1f}]")
print(f"errors: {errs}")
print(f"total climb events: {climbs_total}")

out = {"arm": "prog_haiku", "bests": {str(s): round(b, 6) for s, b in zip(SEEDS, bests)},
       "mean_best": round(mean, 6), "sd_best": round(sd, 6),
       "viable": viable, "valid": valid, "n": len(rows),
       "viable_ci95": [round(vlo * 100, 1), round(vhi * 100, 1)],
       "valid_ci95": [round(glo * 100, 1), round(ghi * 100, 1)],
       "errors": errs, "climb_events": climbs_total}
with open(os.path.join(HERE, "results_armD.json"), "w") as f:
    json.dump(out, f, indent=2)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(7, 4.2))
for s in SEEDS:
    ax.plot(range(10), traj[s], marker="o", ms=3, label=f"seed {s}")
ax.axhline(2.5414213562, color="gray", ls="--", lw=1, label="recall ceiling 2.5414")
ax.axhline(2.6359, color="black", ls=":", lw=1, label="optimum 2.6359")
ax.set_xlabel("generation")
ax.set_ylabel("best-so-far score (sum of radii)")
ax.set_title("Arm D: program evolution, Haiku proposer, unit square")
ax.legend(fontsize=7, loc="lower right")
fig.tight_layout()
fig.savefig(os.path.join(HERE, "figures", "fig4_program_evolution.png"), dpi=150)
print("fig4 written")
