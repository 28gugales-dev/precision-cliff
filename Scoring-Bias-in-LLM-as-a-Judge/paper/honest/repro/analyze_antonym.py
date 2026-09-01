# Antonym-probe analysis -- compute per-family deltas, instruct effect, and
# semantic-conflict metrics from the antonym probe in results_scaled.json.
# Follows the same conventions as analyze_peritem.py.
import json, sys, pathlib, numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results_scaled.json"
SEED = 42
N_BOOT = 10_000

CONTROL = {"antonym": "standard"}
PROBE = "antonym"
VARIANTS = ["standard", "replaced", "flipped"]

def load_pairs(path):
    payload = json.loads(path.read_text())
    results = payload["results"]
    pairs = {}
    for fam, d in results.items():
        if "base" in d and "instruct" in d:
            pairs[fam] = d
    return pairs

def delta(variant_means):
    v = list(variant_means.values())
    return max(v) - min(v)

def boot_ci(arr, rng, n=N_BOOT, alpha=0.05):
    arr = np.asarray(arr, dtype=float)
    means = np.array([rng.choice(arr, size=len(arr), replace=True).mean() for _ in range(n)])
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return round(float(lo), 4), round(float(hi), 4)

def cohen_dz(diffs):
    diffs = np.asarray(diffs, dtype=float)
    if diffs.std() == 0:
        return 0.0
    return round(float(diffs.mean() / diffs.std()), 4)

def main():
    pairs = load_pairs(SRC)
    if not pairs:
        print("ERROR: no paired families found in", SRC)
        sys.exit(1)
    rng = np.random.default_rng(SEED)

    families = sorted(pairs.keys())
    n_fam = len(families)
    print(f"Antonym probe analysis: {n_fam} families from {SRC.name}\n")

    base_deltas = []
    inst_deltas = []
    rows = []

    for fam in families:
        d = pairs[fam]
        if PROBE not in d.get("base", {}) or PROBE not in d.get("instruct", {}):
            print(f"  SKIP {fam}: antonym probe not found")
            continue
        b_means = {v: d["base"][PROBE][v]["mean"] for v in VARIANTS if v in d["base"][PROBE]}
        i_means = {v: d["instruct"][PROBE][v]["mean"] for v in VARIANTS if v in d["instruct"][PROBE]}
        bd = delta(b_means)
        idl = delta(i_means)
        base_deltas.append(bd)
        inst_deltas.append(idl)

        b_ent = {v: d["base"][PROBE][v]["mean_entropy"] for v in b_means}
        i_ent = {v: d["instruct"][PROBE][v]["mean_entropy"] for v in i_means}

        rows.append({
            "family": fam,
            "params_b": d.get("params_b"),
            "base_means": {k: round(v, 4) for k, v in b_means.items()},
            "inst_means": {k: round(v, 4) for k, v in i_means.items()},
            "base_delta": round(bd, 4),
            "inst_delta": round(idl, 4),
            "delta_change": round(idl - bd, 4),
            "base_entropy": {k: round(v, 4) for k, v in b_ent.items()},
            "inst_entropy": {k: round(v, 4) for k, v in i_ent.items()},
        })
        print(f"  {fam:22s}  base_delta={bd:.4f}  inst_delta={idl:.4f}  change={idl-bd:+.4f}")

    base_arr = np.array(base_deltas)
    inst_arr = np.array(inst_deltas)
    diffs = inst_arr - base_arr

    n_inc = int(np.sum(diffs > 0))
    n_dec = int(np.sum(diffs < 0))
    mean_diff = float(diffs.mean())
    ci = boot_ci(diffs, rng)
    dz = cohen_dz(diffs)
    if len(diffs) >= 3:
        wstat, wpval = stats.wilcoxon(base_arr, inst_arr)
    else:
        wstat, wpval = float("nan"), float("nan")

    print(f"\n--- Antonym probe summary ({len(rows)} families) ---")
    print(f"  Mean base delta:    {base_arr.mean():.4f}")
    print(f"  Mean instruct delta:{inst_arr.mean():.4f}")
    print(f"  Mean change (I-B):  {mean_diff:+.4f}  95% CI [{ci[0]:.4f}, {ci[1]:.4f}]")
    print(f"  Cohen's dz:         {dz:.4f}")
    print(f"  Wilcoxon p:         {wpval:.6f}")
    print(f"  Increased/decreased:{n_inc}/{n_dec}")

    replaced_shift_b = []
    replaced_shift_i = []
    flipped_shift_b = []
    flipped_shift_i = []
    for r in rows:
        bm = r["base_means"]
        im = r["inst_means"]
        if "standard" in bm and "replaced" in bm:
            replaced_shift_b.append(bm["replaced"] - bm["standard"])
        if "standard" in im and "replaced" in im:
            replaced_shift_i.append(im["replaced"] - im["standard"])
        if "standard" in bm and "flipped" in bm:
            flipped_shift_b.append(bm["flipped"] - bm["standard"])
        if "standard" in im and "flipped" in im:
            flipped_shift_i.append(im["flipped"] - im["standard"])

    replaced_shift_b = np.array(replaced_shift_b)
    replaced_shift_i = np.array(replaced_shift_i)
    flipped_shift_b = np.array(flipped_shift_b)
    flipped_shift_i = np.array(flipped_shift_i)

    print(f"\n--- Token-replacement effect (replaced - standard) ---")
    print(f"  Base mean shift:    {replaced_shift_b.mean():+.4f}")
    print(f"  Instruct mean shift:{replaced_shift_i.mean():+.4f}")

    print(f"\n--- Semantic-conflict effect (flipped - standard) ---")
    print(f"  Base mean shift:    {flipped_shift_b.mean():+.4f}")
    print(f"  Instruct mean shift:{flipped_shift_i.mean():+.4f}")

    conflict_diffs = np.abs(flipped_shift_i) - np.abs(flipped_shift_b)
    print(f"  |Instruct shift| - |Base shift|: {conflict_diffs.mean():+.4f}")

    summary = {
        "n_families": len(rows),
        "probe": PROBE,
        "mean_base_delta": round(float(base_arr.mean()), 4),
        "mean_inst_delta": round(float(inst_arr.mean()), 4),
        "mean_change": round(mean_diff, 4),
        "ci_95": ci,
        "cohen_dz": dz,
        "wilcoxon_p": round(float(wpval), 6),
        "n_increased": n_inc,
        "n_decreased": n_dec,
        "replaced_shift_base_mean": round(float(replaced_shift_b.mean()), 4),
        "replaced_shift_inst_mean": round(float(replaced_shift_i.mean()), 4),
        "flipped_shift_base_mean": round(float(flipped_shift_b.mean()), 4),
        "flipped_shift_inst_mean": round(float(flipped_shift_i.mean()), 4),
        "conflict_amplification_mean": round(float(conflict_diffs.mean()), 4),
        "per_family": rows,
    }
    out = HERE / "results_antonym_analysis.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"\nWrote {out}")

if __name__ == "__main__":
    main()
