#!/usr/bin/env python
"""Stats + registered-prediction audit for the pinned-API rerun
(api_rerun_pinned.py; R1-R4 in its header). Reads only the jsonl."""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
CAND = os.path.join(BASE, "api_rerun_output", "candidates_api_rerun.jsonl")
OUT = os.path.join(BASE, "results_api_rerun.json")
ATTRACTOR = 2.541421
CEIL = 2.5415
NEAR = 5e-4
SEEDS = [42, 123, 456, 789, 1111]
BASELINE = 0.89999


def main():
    rows = [json.loads(l) for l in open(CAND)]
    assert all(r["reconstructed"] is False for r in rows)
    out = {"n_rows": len(rows),
           "model_ids": sorted({r["model_id"] for r in rows}),
           "params": {"temperature": rows[0]["temperature"],
                      "top_p": rows[0]["top_p"],
                      "max_tokens": rows[0]["max_tokens"],
                      "anthropic_version": rows[0]["anthropic_version"],
                      "thinking": rows[0]["thinking"]}}

    for phase in ("bestof50_sonnet", "bestof50_haiku"):
        p = [r for r in rows if r["phase"] == phase]
        valid = [r for r in p if r["valid"]]
        scores = [r["score"] for r in valid]
        out[phase] = {
            "n": len(p), "viable": sum(r["viable"] for r in p),
            "valid": len(valid),
            "best": round(max(scores), 6) if scores else None,
            "near_attractor": sum(abs(s - ATTRACTOR) <= NEAR for s in scores),
            "above_ceiling": sum(s > CEIL for s in scores),
        }

    loop = [r for r in rows if r["phase"] == "loop_sonnet"]
    per_seed = {}
    for s in SEEDS:
        lin = sorted((r for r in loop if r["seed"] == s),
                     key=lambda r: r["gen"])
        best = BASELINE
        for r in lin:
            if r["valid"]:
                best = max(best, r["score"])
        per_seed[s] = {
            "gens": len(lin), "final_best": round(best, 6),
            "converged_attractor": abs(best - ATTRACTOR) <= 5e-7,
            "echoes": sum(r["coord_echo_parent"] for r in lin),
            "valid": sum(r["valid"] for r in lin),
        }
    lv = [r["score"] for r in loop if r["valid"]]
    out["loop_sonnet"] = {
        "n": len(loop), "valid": sum(r["valid"] for r in loop),
        "per_seed": per_seed,
        "seeds_converged": sum(per_seed[s]["converged_attractor"]
                               for s in SEEDS),
        "above_ceiling": sum(s > CEIL for s in lv),
        "loop_max": round(max(lv), 6) if lv else None,
        "echo_total": sum(r["coord_echo_parent"] for r in loop),
    }

    ls = out["loop_sonnet"]
    bs = out["bestof50_sonnet"]
    bh = out["bestof50_haiku"]
    out["_prereg_audit"] = {
        "R1_loop_convergence": (ls["seeds_converged"] >= 3
                                and ls["above_ceiling"] == 0),
        "R2_sonnet_ceiling": (bs["best"] == ATTRACTOR
                              and bs["above_ceiling"] == 0
                              and bs["valid"] > 0
                              and bs["near_attractor"] / bs["valid"] >= 0.40),
        "R3_haiku_ceiling": (bh["best"] == ATTRACTOR
                             and bh["above_ceiling"] == 0),
        "R4_reduction_loopmax_eq_bestofN": ls["loop_max"] == bs["best"],
    }
    json.dump(out, open(OUT, "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
