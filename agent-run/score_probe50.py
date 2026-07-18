#!/usr/bin/env python
"""Best-of-50 zero-shot control: score raw probe outputs in probe50/ with the
same deterministic evaluator rules as harness.py (EPS=1e-6) and append one
jsonl row per NEW file to probes_bestof50.jsonl (reconstructed:false, logged
at evaluation time). Idempotent: files already logged are skipped.

Files: probe50/haiku_zs_NN.txt, probe50/sonnet_zs_NN.txt (verbatim agent output).
"""
import ast
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PDIR = os.path.join(HERE, "probe50")
OUT = os.path.join(HERE, "probes_bestof50.jsonl")
EPS = 1e-6
N = 26


def parse(text):
    t = re.sub(r"```[a-zA-Z]*", "", text).replace("```", "").strip()
    i, j = t.find("["), t.rfind("]")
    if i == -1 or j == -1:
        return None
    try:
        v = ast.literal_eval(t[i:j + 1])
    except (ValueError, SyntaxError):
        return None
    if not isinstance(v, list):
        return None
    out = []
    for c in v:
        if not (isinstance(c, (list, tuple)) and len(c) == 3):
            return None
        try:
            out.append((float(c[0]), float(c[1]), float(c[2])))
        except (TypeError, ValueError):
            return None
    return out


def evaluate(circles):
    viable = circles is not None and len(circles) == N and all(r > 0 for _, _, r in circles)
    if not viable:
        return {"viable": False, "valid": False, "score": 0.0,
                "n_circles": 0 if circles is None else len(circles)}
    valid = True
    for x, y, r in circles:
        if x - r < -EPS or x + r > 1 + EPS or y - r < -EPS or y + r > 1 + EPS:
            valid = False
    if valid:
        for a in range(N):
            for b in range(a + 1, N):
                xa, ya, ra = circles[a]
                xb, yb, rb = circles[b]
                if ((xa - xb) ** 2 + (ya - yb) ** 2) ** 0.5 < ra + rb - EPS:
                    valid = False
                    break
            if not valid:
                break
    return {"viable": True, "valid": valid,
            "score": round(sum(r for _, _, r in circles), 6) if valid else 0.0,
            "n_circles": N}


done = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8"):
        done.add(json.loads(line)["file"])

new = 0
with open(OUT, "a", encoding="utf-8") as f:
    for fn in sorted(os.listdir(PDIR)):
        if not fn.endswith(".txt") or fn in done:
            continue
        text = open(os.path.join(PDIR, fn), encoding="utf-8").read()
        m = re.match(r"(haiku|sonnet)_zs_(\d+)", fn)
        row = {"arm": "bestof50_zeroshot", "proposer": f"claude-{m.group(1)}",
               "probe": int(m.group(2)), "file": fn,
               **evaluate(parse(text)),
               "logged_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "reconstructed": False}
        f.write(json.dumps(row) + "\n")
        f.flush()
        os.fsync(f.fileno())
        new += 1

rows = [json.loads(l) for l in open(OUT, encoding="utf-8")]
for prop in ("claude-haiku", "claude-sonnet"):
    pr = [r for r in rows if r["proposer"] == prop]
    if not pr:
        continue
    valid = [r for r in pr if r["valid"]]
    best = max((r["score"] for r in valid), default=0.0)
    canon = sum(1 for r in valid if abs(r["score"] - 2.5414) < 5e-4)
    above = sum(1 for r in valid if r["score"] > 2.5415)
    print(f"{prop}: n={len(pr)} viable={sum(r['viable'] for r in pr)} "
          f"valid={len(valid)} best={best:.6f} canonical~2.5414={canon} above_ceiling={above}")
print(f"logged {new} new rows; total {len(rows)}")
