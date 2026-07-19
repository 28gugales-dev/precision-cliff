#!/usr/bin/env python
"""Reproducibility repair of the Claude arms (Future Work item 8):
rerun Arm B's loop and the best-of-50 zero-shot control through the DATED,
PARAMETER-LOGGED Anthropic Messages API.

Every request logs: resolved model id (dated where the API exposes one),
temperature, top_p (null = API default), max_tokens, anthropic-version
header, request UTC timestamp, response id, stop_reason, and token usage.
Thinking/extended reasoning is NOT enabled. No tools. No system prompt.
Every raw response body text is archived verbatim to
api_rerun_output/raw/ BEFORE parsing; one jsonl row per invocation is
appended at evaluation time with reconstructed:false. Checkpointed and
resumable (completed invocations are skipped by jsonl index).

Protocol notes (disclosed in the paper):
- The original Arms A-D ran 2026-07-17 through the Claude Code agent
  runtime under undated aliases with unlogged sampling settings; at run
  time those aliases resolved to the same model generation used here
  (Sonnet 5 / Haiku 4.5), but that resolution is not post-hoc verifiable.
  This rerun makes the model identity and sampling parameters explicit.
- The loop rerun is a single-turn completion per generation (parent
  packing serialized in-message, A.5-style) rather than a file-writing
  agent; the prompt keeps A.1's return-parent clause and task text. The
  best-of-50 prompt is A.6 verbatim. Running loop and control through
  the SAME invocation mode also mode-matches the paper's central
  loop-vs-best-of-N comparison.
- API sampling is not seedable; harness seeds control tie-breaking only,
  as in every other arm.

PREREGISTERED PREDICTIONS - written before this run executed; the push
of this file to github.com/28gugales-dev/precision-cliff timestamps it
ahead of execution. Original values in parentheses.
  R1 (loop convergence): >=3/5 loop seeds end with best == 2.541421
     (6 dp) and 0/50 valid loop candidates score > 2.5415.
     (Original Arm B: 4/5 seeds at 2.541421, seed 1111 at 2.523367,
      0 above.)
  R2 (control ceiling, sonnet): best valid sample == 2.541421 (6 dp),
     0/50 valid samples > 2.5415, >=40% of valid samples within 5e-4 of
     2.541421. (Original: 50/50 valid, best 2.541421, 29 near, 0 above.)
  R3 (control ceiling, haiku): best valid sample == 2.541421 (6 dp),
     0 valid samples > 2.5415. (Original: 45/50 valid, best 2.541421,
     28 near, 0 above.)
  R4 (reduction): loop max == sonnet best-of-50 max at 6 dp.
  Failure rule: ANY valid output above 2.5415 falsifies the attractor-
  ceiling claim for the pinned models and must be reported prominently,
  not explained away. Prediction failures are reported as failures.
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

import harness            # parse_proposal, baseline_packing, N, EPS
import harness_v2         # evaluate(circles, W, H)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "api_rerun_output")
RAW_DIR = os.path.join(OUT_DIR, "raw")
CAND_LOG = os.path.join(OUT_DIR, "candidates_api_rerun.jsonl")
PROV = os.path.join(OUT_DIR, "provenance.json")

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
SEEDS = [42, 123, 456, 789, 1111]
GENS = 10
N_BESTOF = 50
TEMPERATURE = 1.0
MAX_TOKENS = 4096
MODEL_PREFS = {          # alias -> preference order for dated ids
    "sonnet": ["claude-sonnet-5"],
    "haiku": ["claude-haiku-4-5-20251001", "claude-haiku-4-5"],
}

BESTOF50_PROMPT = (
    "Pack exactly 26 non-overlapping circles inside the unit square [0,1]x[0,1] "
    "so that the sum of their radii is as large as possible. MUST hold: exactly "
    "26 circles; every circle fully inside the unit square (x-r >= 0, x+r <= 1, "
    "same for y); no two circles overlap (distance between centers >= sum of the "
    "two radii; touching is allowed). Do not use any tools and do not run any "
    "code - the packing must come from your own reasoning. Your entire reply "
    "must be ONLY the raw Python list of 26 [x, y, r] lists. No explanation, no "
    "code fences, no other text."
)

LOOP_PROMPT = (
    "You are the proposal step of an evolutionary search for circle packings.\n"
    "Current best packing (sum of radii = {best_score}):\n"
    "{packing}\n\n"
    "Produce a packing of exactly 26 circles with a HIGHER sum of radii than "
    "best_score if you can; if you cannot find a strictly better valid packing, "
    "return the parent unchanged. MUST hold: exactly 26 circles; every circle "
    "fully inside the unit square [0,1]x[0,1] (x-r >= 0, x+r <= 1, same for y); "
    "no two circles overlap (distance between centers >= sum of the two radii; "
    "touching is allowed). Do not use any tools and do not run any code - the "
    "packing must come from your own reasoning. Output ONLY the raw Python list "
    "of 26 [x, y, r] lists. No explanation, no code fences, no other text."
)


def canon(circles):
    return tuple(sorted(tuple(round(v, 6) for v in c) for c in circles))


def api_key():
    k = os.environ.get("ANTHROPIC_API_KEY")
    if not k:
        sys.exit("ANTHROPIC_API_KEY not set. Set it in your own shell "
                 "(never paste it into chat) and rerun.")
    return k


def resolve_models(key):
    """Resolve aliases to the most specific (dated) ids the API exposes;
    archive the matching model-list entries in provenance."""
    r = requests.get("https://api.anthropic.com/v1/models?limit=100",
                     headers={"x-api-key": key,
                              "anthropic-version": API_VERSION},
                     timeout=30)
    r.raise_for_status()
    entries = r.json()["data"]
    ids = {e["id"]: e for e in entries}
    resolved, prov_entries = {}, {}
    for alias, prefs in MODEL_PREFS.items():
        pick = None
        for p in prefs:
            dated = sorted(i for i in ids if i.startswith(p + "-2"))
            if dated:
                pick = dated[-1]
                break
            if p in ids:
                pick = p
                break
        if pick is None:
            sys.exit(f"no model found for alias {alias} (prefs {prefs})")
        resolved[alias] = pick
        prov_entries[alias] = ids[pick]
    return resolved, prov_entries


def call_api(key, model, prompt):
    body = {"model": model, "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "messages": [{"role": "user", "content": prompt}]}
    for attempt in range(6):
        ts = datetime.now(timezone.utc).isoformat()
        try:
            r = requests.post(API_URL, json=body, timeout=600,
                              headers={"x-api-key": key,
                                       "anthropic-version": API_VERSION,
                                       "content-type": "application/json"})
        except requests.RequestException as e:
            print(f"  network error ({e}); retry {attempt + 1}")
            time.sleep(15 * (attempt + 1))
            continue
        if r.status_code == 200:
            d = r.json()
            text = "".join(b["text"] for b in d["content"]
                           if b["type"] == "text")
            return text, {
                "model_id": d["model"], "response_id": d["id"],
                "stop_reason": d["stop_reason"],
                "input_tokens": d["usage"]["input_tokens"],
                "output_tokens": d["usage"]["output_tokens"],
                "request_ts_utc": ts, "temperature": TEMPERATURE,
                "top_p": None, "max_tokens": MAX_TOKENS,
                "anthropic_version": API_VERSION, "thinking": "disabled",
            }
        if r.status_code in (429, 500, 502, 503, 529):
            wait = int(r.headers.get("retry-after", 20 * (attempt + 1)))
            print(f"  HTTP {r.status_code}; wait {wait}s")
            time.sleep(wait)
            continue
        sys.exit(f"API error {r.status_code}: {r.text[:500]}")
    sys.exit("giving up after 6 attempts")


def load_done():
    done = set()
    if os.path.exists(CAND_LOG):
        for line in open(CAND_LOG):
            r = json.loads(line)
            done.add((r["phase"], r.get("seed"), r["idx"]))
    return done


def log_row(row):
    with open(CAND_LOG, "a") as f:
        f.write(json.dumps(row) + "\n")
        f.flush()
        os.fsync(f.fileno())
    print(f"JSONL|{json.dumps(row)}")


def save_raw(name, text):
    p = os.path.join(RAW_DIR, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return os.path.relpath(p, HERE).replace(os.sep, "/")


def self_test():
    base = harness.baseline_packing()
    ev = harness_v2.evaluate(base, 1.0, 1.0)
    assert ev["valid"] and abs(ev["score"] - 0.89999) < 1e-5, ev
    c, err = harness.parse_proposal("[[0.1, 0.1, 0.05]] junk")
    assert c is not None and err is None
    assert canon(base) == canon(list(reversed(base)))
    lp = LOOP_PROMPT.format(best_score="0.89999", packing=json.dumps(base))
    assert "HIGHER" in lp and "return the parent" in lp
    print("self_test OK")


def run_bestof50(key, alias, model, done):
    phase = f"bestof50_{alias}"
    for i in range(1, N_BESTOF + 1):
        if (phase, None, i) in done:
            continue
        text, meta = call_api(key, model, BESTOF50_PROMPT)
        raw = save_raw(f"{phase}_{i:02d}.txt", text)
        circles, perr = harness.parse_proposal(text)
        ev = harness_v2.evaluate(circles, 1.0, 1.0)
        log_row({"phase": phase, "proposer_alias": alias, "seed": None,
                 "idx": i, "score": round(ev["score"], 6),
                 "viable": ev["viable"], "valid": ev["valid"],
                 "n_circles": ev["n"], "parse_error": perr,
                 "raw_path": raw, "reconstructed": False, **meta})


def run_loop(key, alias, model, done):
    phase = f"loop_{alias}"
    for s in SEEDS:
        parent = harness.baseline_packing()
        parent_score = 0.89999
        for g in range(GENS):
            idx = g
            if (phase, s, idx) in done:
                # rebuild lineage state from the log
                for line in open(CAND_LOG):
                    r = json.loads(line)
                    if (r["phase"], r["seed"], r["idx"]) == (phase, s, idx):
                        if r["valid"] and r["score"] > parent_score:
                            rc = json.load(open(os.path.join(
                                HERE, r["raw_circles_path"])))
                            parent, parent_score = rc, r["score"]
                        break
                continue
            prompt = LOOP_PROMPT.format(
                best_score=f"{parent_score:.6f}",
                packing=json.dumps([[round(v, 6) for v in c]
                                    for c in parent]))
            text, meta = call_api(key, model, prompt)
            raw = save_raw(f"{phase}_seed{s}_gen{g}.txt", text)
            circles, perr = harness.parse_proposal(text)
            ev = harness_v2.evaluate(circles, 1.0, 1.0)
            echo = bool(ev["valid"] and circles is not None
                        and canon(circles) == canon(parent))
            row = {"phase": phase, "proposer_alias": alias, "seed": s,
                   "idx": idx, "gen": g,
                   "parent_score": round(parent_score, 6),
                   "score": round(ev["score"], 6), "viable": ev["viable"],
                   "valid": ev["valid"], "n_circles": ev["n"],
                   "coord_echo_parent": echo, "parse_error": perr,
                   "raw_path": raw, "reconstructed": False, **meta}
            if ev["valid"] and ev["score"] > parent_score:
                cp = os.path.join(RAW_DIR,
                                  f"{phase}_seed{s}_gen{g}_accepted.json")
                json.dump(circles, open(cp, "w"))
                row["raw_circles_path"] = os.path.relpath(
                    cp, HERE).replace(os.sep, "/")
                parent, parent_score = circles, ev["score"]
            log_row(row)
        print(f"{phase} seed {s}: final best {parent_score:.6f}")


def main():
    self_test()
    if "--selftest" in sys.argv:
        return
    key = api_key()
    os.makedirs(RAW_DIR, exist_ok=True)
    resolved, prov_entries = resolve_models(key)
    prov = {"script_sha256": hashlib.sha256(
                open(__file__, "rb").read()).hexdigest(),
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "resolved_models": resolved, "model_entries": prov_entries,
            "anthropic_version": API_VERSION,
            "temperature": TEMPERATURE, "top_p": "API default (unset)",
            "max_tokens": MAX_TOKENS, "thinking": "disabled",
            "system_prompt": None}
    json.dump(prov, open(PROV, "w"), indent=2)
    print("models:", resolved)
    done = load_done()
    run_bestof50(key, "sonnet", resolved["sonnet"], done)
    run_bestof50(key, "haiku", resolved["haiku"], done)
    run_loop(key, "sonnet", resolved["sonnet"], done)
    print("[done] all phases complete")


if __name__ == "__main__":
    main()
