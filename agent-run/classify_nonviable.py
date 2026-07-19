#!/usr/bin/env python
"""Classify non-viable / invalid rows in the 14B circle-packing precision-sweep
jsonl logs (v2 re-execution, fresh-seed run, IQ2 control).

Pure log parsing. No LLM / GPU calls. Reads existing candidates*.jsonl files,
reconstructs the per-lineage RUNNING parent using the same convention as
stats_precision_14b_fresh.py, and bins every valid==false row into:

  circles present (parsed, non-viable/invalid):
    near_copy            >=50% of the row's circle triples (round 6dp) coincide
                          with the running parent's triples
    attempted_mutation   <50% overlap with parent

  circles absent, raw present (parse failure):
    attempted_packing_broken  raw has >=10 "[x, y, r]"-like numeric triples
                               (sub-flag partial_copy if extracted-triple
                               overlap with running parent >=50%)
    garbage_or_truncation     fewer than 10 such triples

  parse_error starts with "gen_error":
    gen_error             (checked first, independent of circles/raw state)

  anything matching none of the above -> unclassified (never crashes)
"""

import glob
import json
import os
import re
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(BASE, "results_nonviable_classification.json")

N = 26
BASELINE_SCORE = 0.89999
GENS_PER_SEED = 10
TRIPLE_RE = re.compile(
    r"\[\s*[-+]?[\d.]+(?:[eE][-+]?\d+)?\s*,\s*[-+]?[\d.]+(?:[eE][-+]?\d+)?\s*,"
    r"\s*[-+]?[\d.]+(?:[eE][-+]?\d+)?\s*\]"
)
NUM_RE = re.compile(r"[-+]?[\d.]+(?:[eE][-+]?\d+)?")

RUNS = {
    "v2_14b_reexecution": {
        "glob": os.path.join(BASE, "precision_sweep_14b_v2_output", "**", "candidates*.jsonl"),
        "rungs": ["q8_0", "q4_k_m", "q3_k_m", "q2_k"],
        "seeds": [42, 123, 456, 789, 1111],
    },
    "fresh_seed_14b": {
        "glob": os.path.join(
            BASE, "precision_sweep_14b_fresh_output", "**",
            "candidates_precision_14b_fresh.jsonl"),
        "rungs": ["q4_k_m", "q2_k"],
        "seeds": [2222, 3333, 5555, 7777, 9999],
    },
    "iq2_control_14b": {
        "glob": os.path.join(
            BASE, "precision_sweep_14b_iq2_output", "**",
            "candidates_precision_14b_iq2.jsonl"),
        "rungs": ["q2_k_imx", "iq2_m"],
        "seeds": [2222, 3333, 5555, 7777, 9999],
    },
}


def baseline_packing():
    r = round(0.9 / N, 6)
    pts = []
    for row in range(5):
        for col in range(6):
            if len(pts) >= N:
                break
            pts.append([round((col + 0.5) / 6.0, 6), round((row + 0.5) / 5.0, 6), r])
    return pts


def round_triple(c):
    return tuple(round(float(v), 6) for v in c)


def triples_counter(circles):
    return Counter(round_triple(c) for c in circles)


def extract_triples_from_raw(raw):
    triples = []
    for m in TRIPLE_RE.finditer(raw):
        nums = NUM_RE.findall(m.group(0))
        if len(nums) == 3:
            try:
                triples.append(tuple(round(float(x), 6) for x in nums))
            except ValueError:
                pass
    return triples


def classify_row(row, parent_counter):
    pe = row.get("parse_error")
    if pe and str(pe).startswith("gen_error"):
        return "gen_error", {}

    circles = row.get("circles")
    if circles is not None:
        denom = len(circles)
        rc = triples_counter(circles)
        inter = sum((rc & parent_counter).values())
        frac = (inter / denom) if denom else 0.0
        info = {"overlap_frac": round(frac, 3), "n_circles": denom}
        if denom > 0 and frac >= 0.5:
            return "near_copy", info
        return "attempted_mutation", info

    raw = row.get("raw")
    if raw:
        triples = extract_triples_from_raw(raw)
        n_tri = len(triples)
        if n_tri >= 10:
            tc = Counter(triples)
            inter = sum((tc & parent_counter).values())
            frac = (inter / n_tri) if n_tri else 0.0
            info = {"n_triples": n_tri, "overlap_frac": round(frac, 3),
                     "partial_copy": frac >= 0.5}
            return "attempted_packing_broken", info
        return "garbage_or_truncation", {"n_triples": n_tri}

    return "unclassified", {}


def find_candidates_file(pattern):
    matches = sorted(glob.glob(pattern, recursive=True))
    matches = [m for m in matches if "mustdiffer" not in os.path.basename(m)]
    if not matches:
        raise FileNotFoundError(f"no candidates*.jsonl matched {pattern}")
    if len(matches) > 1:
        raise RuntimeError(f"ambiguous match for {pattern}: {matches}")
    return matches[0]


def empty_bin_counts():
    return {
        "near_copy": 0,
        "attempted_mutation": 0,
        "attempted_packing_broken": 0,
        "attempted_packing_broken_partial_copy": 0,
        "garbage_or_truncation": 0,
        "gen_error": 0,
        "unclassified": 0,
    }


def main():
    out = {}
    for run_name, cfg in RUNS.items():
        path = find_candidates_file(cfg["glob"])
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        assert all(r.get("reconstructed") is False for r in rows), \
            f"{run_name}: reconstructed row found in {path}"

        run_out = {"source_file": path, "rungs": {}}
        for rung in cfg["rungs"]:
            rrows = [r for r in rows if r["quant"] == rung]
            expected_total = len(cfg["seeds"]) * GENS_PER_SEED
            assert len(rrows) == expected_total, (
                f"{run_name}/{rung}: expected {expected_total} rows, got "
                f"{len(rrows)}")

            bins = empty_bin_counts()
            examples = {k: [] for k in bins}
            n_valid = 0

            for seed in cfg["seeds"]:
                lineage = sorted(
                    (r for r in rrows if r["seed"] == seed),
                    key=lambda r: r["gen"])
                parent_circles = baseline_packing()
                parent_score = BASELINE_SCORE

                for r in lineage:
                    if r["valid"]:
                        n_valid += 1
                    else:
                        parent_counter = triples_counter(parent_circles)
                        bin_name, info = classify_row(r, parent_counter)
                        bins[bin_name] += 1
                        if bin_name == "attempted_packing_broken" and info.get("partial_copy"):
                            bins["attempted_packing_broken_partial_copy"] += 1
                        if len(examples[bin_name]) < 3:
                            examples[bin_name].append({
                                "seed": r["seed"], "gen": r["gen"], **info})

                    # advance running parent (same rule regardless of bin)
                    if r["valid"] and r["score"] > parent_score:
                        parent_score = r["score"]
                        parent_circles = r["circles"]

            n_invalid = expected_total - n_valid
            partitioned = (bins["near_copy"] + bins["attempted_mutation"]
                           + bins["attempted_packing_broken"]
                           + bins["garbage_or_truncation"]
                           + bins["gen_error"] + bins["unclassified"])
            assert partitioned == n_invalid, (
                f"{run_name}/{rung}: bins sum {partitioned} != invalid rows "
                f"{n_invalid}")

            run_out["rungs"][rung] = {
                "total_rows": expected_total,
                "valid": n_valid,
                "invalid": n_invalid,
                "bins": bins,
                "examples": examples,
            }
        out[run_name] = run_out

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
