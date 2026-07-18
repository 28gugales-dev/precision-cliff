#!/usr/bin/env python
"""Figure 1 (regenerated): Arm A best-so-far vs generation, per seed, with a
small constant vertical offset per seed so coincident trajectories (e.g. seeds
42 and 789) remain individually visible instead of occluding."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "candidates.jsonl"))]
seeds = sorted({r["seed"] for r in rows})

fig, ax = plt.subplots(figsize=(7.5, 4.4))
colors = ["#1668dc", "#d4380d", "#389e0d", "#722ed1", "#d48806"]
for k, s in enumerate(seeds):
    sr = sorted((r for r in rows if r["seed"] == s), key=lambda r: r["gen"])
    best, ys, xs = 0.89999, [], []
    for r in sr:
        if r["valid"] and r["score"] > best:
            best = r["score"]
        xs.append(r["gen"])
        ys.append(best)
    off = (k - 2) * 0.004  # display-only jitter; values printed in legend
    ax.plot(xs, [y + off for y in ys], marker="o", ms=3.5, lw=1.4,
            color=colors[k], label=f"seed {s} (final {ys[-1]:.4f})")
ax.axhline(2.541421, color="#8c8c8c", ls="--", lw=1,
           label="constructible attractor 2.541421")
ax.set_xlabel("generation")
ax.set_ylabel("best-so-far (sum of radii)")
ax.set_title("Arm A: best-so-far per seed\n(curves offset vertically by 0.004 "
             "steps for visibility; true finals in legend)")
ax.legend(fontsize=7.5, loc="lower right")
fig.tight_layout()
fig.savefig(os.path.join(HERE, "figures", "fig1_fitness_vs_gen.png"), dpi=150)
print("fig1 written")
