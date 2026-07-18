#!/usr/bin/env python
"""
Precision-sweep visualization. Run AFTER dropping the downloaded Kaggle folder at
research-corpus/agent-run/precision_sweep/ :

    python make_fig5_precision.py

Produces in figures/:
    fig5_precision_cliff.png    viability/validity vs bits + score-vs-ceiling panel
    fig6_packing_portraits.png  best actual packing per precision, drawn as circles
    fig7_count_drift.png        n_circles distribution per precision (target: 26)
"""
import json
import math
import os
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle as MplCircle

HERE = os.path.dirname(os.path.abspath(__file__))
SWEEP = os.path.join(HERE, "precision_sweep")
FIGS = os.path.join(HERE, "figures")
STATE = os.path.join(SWEEP, "state")

QUANTS = [("fp16", 16.0), ("q8_0", 8.5), ("q4_k_m", 4.85), ("q3_k_m", 3.91), ("q2_k", 3.35)]
SEEDS = [42, 123, 456, 789, 1111]
CEILING = 2.5414213562
OPTIMUM = 2.6359
HAIKU_VIABILITY = 0.98  # paper Arm A reference


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / d, (c + m) / d


rows = [json.loads(l) for l in open(os.path.join(SWEEP, "candidates_precision.jsonl"))]
have = [q for q, _ in QUANTS if any(r["quant"] == q for r in rows)]
print(f"loaded {len(rows)} rows; quants present: {have}")

# ---------- fig5: the cliff + capability gap ----------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

xs, viab, vlo, vhi, valid, alo, ahi = [], [], [], [], [], [], []
for q, bits in QUANTS:
    qr = [r for r in rows if r["quant"] == q]
    if not qr:
        continue
    xs.append(bits)
    k = sum(1 for r in qr if r["viable"])
    lo, hi = wilson(k, len(qr))
    viab.append(100 * k / len(qr)); vlo.append(100 * lo); vhi.append(100 * hi)
    k2 = sum(1 for r in qr if r["valid"])
    lo2, hi2 = wilson(k2, len(qr))
    valid.append(100 * k2 / len(qr)); alo.append(100 * lo2); ahi.append(100 * hi2)

ax1.plot(xs, viab, "o-", color="#1668dc", label="viable (parses to 26 circles)")
ax1.fill_between(xs, vlo, vhi, color="#1668dc", alpha=0.15)
ax1.plot(xs, valid, "s-", color="#d4380d", label="valid (geometry holds)")
ax1.fill_between(xs, alo, ahi, color="#d4380d", alpha=0.15)
ax1.axhline(HAIKU_VIABILITY * 100, color="gray", ls="--", lw=1,
            label="Claude Haiku viability (Arm A, 98%)")
ax1.set_xlabel("effective bits per weight")
ax1.set_ylabel("% of 50 loop candidates")
ax1.set_title("Viability / validity vs precision")
ax1.set_ylim(-3, 105)
ax1.invert_xaxis()
ax1.legend(fontsize=7)

for q, bits in QUANTS:
    qr = [r for r in rows if r["quant"] == q]
    if not qr:
        continue
    bests = []
    for s in SEEDS:
        b = max((r["score"] for r in qr if r["seed"] == s and r["valid"]), default=0.0)
        bests.append(b)
    ax2.scatter([bits] * len(bests), bests, s=28, alpha=0.75, label=None)
    ax2.scatter([bits], [sum(bests) / len(bests)], marker="_", s=500, color="black")
ax2.axhline(CEILING, color="gray", ls="--", lw=1, label="recall ceiling 2.5414 (Haiku/Sonnet)")
ax2.axhline(OPTIMUM, color="black", ls=":", lw=1, label="optimum 2.6359")
ax2.axhline(0.89999, color="#52c41a", ls="-.", lw=1, label="harness baseline 0.900")
ax2.set_xlabel("effective bits per weight")
ax2.set_ylabel("best valid score per seed (sum of radii)")
ax2.set_title("Best score vs precision (dots = seeds, bar = mean)")
ax2.invert_xaxis()
ax2.legend(fontsize=7, loc="center right")
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig5_precision_cliff.png"), dpi=150)
print("fig5 written")

# ---------- fig6: packing portraits ------------------------------------------
present = [q for q, _ in QUANTS if any(r["quant"] == q for r in rows)]
fig, axes = plt.subplots(1, len(present), figsize=(3.1 * len(present), 3.4))
if len(present) == 1:
    axes = [axes]
for ax, q in zip(axes, present):
    best_circ, best_score = None, -1.0
    for s in SEEDS:
        sp = os.path.join(STATE, f"{q}_seed_{s}.json")
        if not os.path.exists(sp):
            continue
        st = json.load(open(sp))
        if st["best_score"] > best_score:
            best_score = st["best_score"]
            best_circ = st["best_circles"]
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    if best_circ:
        for (x, y, r) in best_circ:
            ax.add_patch(MplCircle((x, y), r, facecolor="#1668dc",
                                   edgecolor="#0b3d91", alpha=0.55, lw=0.8))
    ax.set_title(f"{q}\nbest={best_score:.4f}", fontsize=9)
fig.suptitle("Best packing found per precision (baseline grid = no improvement found)",
             fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig6_packing_portraits.png"), dpi=150)
print("fig6 written")

# ---------- fig7: circle-count drift ------------------------------------------
fig, ax = plt.subplots(figsize=(8, 4))
width = 0.15
for i, (q, _) in enumerate([qb for qb in QUANTS if qb[0] in present]):
    qr = [r for r in rows if r["quant"] == q]
    cnt = Counter(min(r["n_circles"], 40) for r in qr)  # clamp tail for display
    ks = sorted(cnt)
    ax.bar([k + (i - 2) * width for k in ks], [cnt[k] for k in ks],
           width=width, label=q, alpha=0.85)
ax.axvline(26, color="black", ls="--", lw=1, label="target: 26")
ax.set_xlabel("circles emitted per proposal (clamped at 40)")
ax.set_ylabel("count of proposals")
ax.set_title("Circle-count drift by precision")
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(FIGS, "fig7_count_drift.png"), dpi=150)
print("fig7 written")
