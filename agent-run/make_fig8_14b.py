#!/usr/bin/env python
"""Figure 8: 14B sweep — flat viability, novelty cliff at 2-bit.
Reads results_precision_14b_local.json + results_precision_local.json (7B)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.join(HERE, "figures")
r14 = json.load(open(os.path.join(HERE, "results_precision_14b_local.json")))["per_quant"]
r7 = json.load(open(os.path.join(HERE, "results_precision_local.json")))["per_quant"]

QUANTS = ["q8_0", "q4_k_m", "q3_k_m", "q2_k"]
BPW = [8.5, 4.85, 3.91, 3.35]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

for label, res, color in [("14B", r14, "#1668dc"), ("7B", r7, "#8c8c8c")]:
    v = [int(res[q]["viable"].split("/")[0]) * 2 for q in QUANTS]
    lo = [res[q]["viable_ci"][0] for q in QUANTS]
    hi = [res[q]["viable_ci"][1] for q in QUANTS]
    ax1.plot(BPW, v, "o-", color=color, label=f"{label} viable")
    ax1.fill_between(BPW, lo, hi, color=color, alpha=0.15)
ax1.axhline(98, color="gray", ls="--", lw=1, label="Claude Haiku (Arm A, 98%)")
ax1.set_xlabel("effective bits per weight")
ax1.set_ylabel("% of 50 loop candidates viable")
ax1.set_title("Viability: scale moves it, precision does not")
ax1.set_ylim(-3, 105)
ax1.invert_xaxis()
ax1.legend(fontsize=8)

# Coordinate-verified echoes from the 2026-07-18 replication (results_precision_14b_v2.json);
# improvement counts unchanged (bit-identical run).
r14v2 = json.load(open(os.path.join(HERE, "results_precision_14b_v2.json")))
improved = [r14v2[q]["seeds_improved"] for q in QUANTS]
echo_frac = [100 * r14v2[q]["coord_echo"] / r14v2[q]["valid_rows"] for q in QUANTS]

# Primary series: coordinate-verified parent-echo rate (bars, prominent).
bars = ax2.bar(BPW, echo_frac, width=0.35, color="#722ed1", alpha=0.85,
                label="valid outputs echoing their parent (coordinate-verified, %)")
ax2.set_xlabel("effective bits per weight")
ax2.set_ylabel("parent-echo rate (%)", color="#722ed1")
ax2.tick_params(axis="y", labelcolor="#722ed1")
ax2.set_ylim(-3, 105)
ax2.invert_xaxis()

# Secondary series: seeds improving past baseline, muted line on twin axis.
ax2b = ax2.twinx()
ax2b.plot(BPW, [i * 20 for i in improved], "o--", color="#bfbfbf", lw=1.3,
          ms=4, alpha=0.8, label="seeds improving past baseline (% of 5)")
ax2b.set_ylabel("seeds improving (%)", color="#8c8c8c")
ax2b.tick_params(axis="y", labelcolor="#8c8c8c")
ax2b.set_ylim(-3, 105)

ax2.set_title(f"novelty cliff: parent-echo spikes at Q2_K "
              f"({echo_frac[0]:.0f}%->{echo_frac[-1]:.0f}%)")
h1, l1 = ax2.get_legend_handles_labels()
h2, l2 = ax2b.get_legend_handles_labels()
ax2.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left")

fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig8_14b_novelty_cliff.png"), dpi=150)
print("fig8 written")
