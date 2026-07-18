#!/usr/bin/env python
"""Figure 9: fresh-seed echo replication (left) + Arm E N-generality (right).
Reads results_precision_14b_v2.json, results_precision_14b_fresh.json, results_v4.json."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.join(HERE, "figures")
v2 = json.load(open(os.path.join(HERE, "results_precision_14b_v2.json")))
fr = json.load(open(os.path.join(HERE, "results_precision_14b_fresh.json")))
v4 = json.load(open(os.path.join(HERE, "results_v4.json")))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

# Left: coordinate-verified echo rate, original seeds vs fresh seeds, plus must-differ.
labels = ["Q4_K_M\noriginal", "Q4_K_M\nfresh", "Q4_K_M\nmust-differ",
          "Q2_K\noriginal", "Q2_K\nfresh", "Q2_K\nmust-differ"]
vals = [100 * v2["q4_k_m"]["coord_echo"] / v2["q4_k_m"]["valid_rows"],
        100 * fr["q4_k_m"]["coord_echo"] / fr["q4_k_m"]["valid_rows"],
        100 * fr["q4_k_m"]["mustdiffer_coord_echo"] / fr["q4_k_m"]["mustdiffer_valid"],
        100 * v2["q2_k"]["coord_echo"] / v2["q2_k"]["valid_rows"],
        100 * fr["q2_k"]["coord_echo"] / fr["q2_k"]["valid_rows"],
        100 * fr["q2_k"]["mustdiffer_coord_echo"] / fr["q2_k"]["mustdiffer_valid"]]
colors = ["#69b1ff", "#1668dc", "#003eb3", "#ffa39e", "#d4380d", "#820014"]
bars = ax1.bar(range(6), vals, color=colors)
for b, v in zip(bars, vals):
    ax1.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}%", ha="center", fontsize=8)
ax1.set_xticks(range(6))
ax1.set_xticklabels(labels, fontsize=7.5)
ax1.set_ylabel("valid outputs echoing parent (coordinate-verified, %)")
ax1.set_ylim(0, 112)
ax1.set_title("Echo cliff replicates on fresh seeds;\ncopying survives an explicit prohibition")

# Right: Arm E per-seed final bests vs constructed analogs.
n23 = [p["best"] for p in v4["n23"]["per_seed"]]
n27 = [p["best"] for p in v4["n27"]["per_seed"]]
ax2.scatter([23] * 5, n23, s=55, color="#1668dc", zorder=3, label="final best per seed")
ax2.scatter([27] * 5, n27, s=55, color="#1668dc", zorder=3)
ax2.hlines(2.5828427, 26.5, 27.5, colors="#d4380d", ls="--",
           label="constructed analog (grid + fillers)")
ax2.hlines(2.3624369, 22.5, 23.5, colors="#d4380d", ls="--")
ax2.hlines(2.300, 22.5, 23.5, colors="#8c8c8c", ls=":",
           label="truncated-template trap (23 × 0.1)")
ax2.set_xticks([23, 27])
ax2.set_xlim(21.5, 28.5)
ax2.set_xlabel("N (circles in unit square)")
ax2.set_ylabel("final best (sum of radii)")
ax2.set_title("Arm E: the attractor is a parametric recipe\n(converge when it fits, trap when it misfits)")
ax2.legend(fontsize=8, loc="lower right")

fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig9_fresh_armE.png"), dpi=150)
print("fig9 written")
