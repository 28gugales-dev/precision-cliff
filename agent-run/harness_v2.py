#!/usr/bin/env python
"""
Arm-aware extension of harness.py for the A-grade revision.

Arms:
  unit_sonnet — unit square [0,1]x[0,1], Claude Sonnet proposer   (tests: does a
                stronger model have a HIGHER recall ceiling than Haiku's 2.5414?)
  rect_haiku  — rectangle [0,1]x[0,0.83], Claude Haiku proposer   (non-memorizable
                variant: no published optimum for 26 circles in 1x0.83, so recall
                cannot supply the answer; tests search vs recall)

Same deterministic evaluator, same live-logging discipline as harness.py.
Rows go to candidates_v2.jsonl with explicit arm + proposer fields.

Commands:
  initall                          init all seeds for both arms
  batchstep <arm> <gen>            evaluate prop_v2/<arm>_seed_<s>_gen_<g>.txt for all seeds
  summary                          write results_v2.json
"""
import sys, os, json, math, time, io, contextlib
import harness  # reuse parse_proposal + cell_of + N + EPS + GRID

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(HERE, "state_v2")
PROP_DIR = os.path.join(HERE, "prop_v2")
CAND_LOG = os.path.join(HERE, "candidates_v2.jsonl")
RESULTS = os.path.join(HERE, "results_v2.json")

SEEDS = [42, 123, 456, 789, 1111]
ARMS = {
    "unit_sonnet": {"W": 1.0, "H": 1.0, "proposer": "claude-sonnet"},
    "rect_haiku":  {"W": 1.0, "H": 0.83, "proposer": "claude-haiku"},
}
N = harness.N
EPS = harness.EPS


def baseline_packing(W, H):
    """Deterministic valid packing: 26 circles on a 6x5 grid inside W x H.
    Unit square uses harness.baseline_packing() verbatim so arm unit_sonnet starts
    from the IDENTICAL baseline (0.89999) as the original haiku arm — only the
    proposer differs. The rectangle arm scales the same recipe (r = 0.9/26 * min(W,H))."""
    if W == 1.0 and H == 1.0:
        return harness.baseline_packing()
    r = (0.9 / N) * min(W, H)
    pts = []
    for row in range(5):
        for col in range(6):
            if len(pts) >= N:
                break
            x = (col + 0.5) * W / 6.0
            y = (row + 0.5) * H / 5.0
            pts.append([round(x, 6), round(y, 6), round(r, 6)])
    return pts


def evaluate(circles, W, H):
    res = {"viable": False, "valid": False, "score": 0.0,
           "mean_radius": 0.0, "density": 0.0, "n": 0 if circles is None else len(circles)}
    if circles is None:
        return res
    res["n"] = len(circles)
    if len(circles) != N or any(r <= 0 for (_, _, r) in circles):
        return res
    res["viable"] = True
    radii = [r for (_, _, r) in circles]
    res["mean_radius"] = sum(radii) / N
    res["density"] = sum(math.pi * r * r for r in radii) / (W * H)
    inside = all((x - r >= -EPS and x + r <= W + EPS and
                  y - r >= -EPS and y + r <= H + EPS) for (x, y, r) in circles)
    overlap = False
    for i in range(N):
        xi, yi, ri = circles[i]
        for j in range(i + 1, N):
            xj, yj, rj = circles[j]
            if math.hypot(xi - xj, yi - yj) + EPS < ri + rj:
                overlap = True
                break
        if overlap:
            break
    if inside and not overlap:
        res["valid"] = True
        res["score"] = sum(radii)
    return res


def spath(arm, seed):
    return os.path.join(STATE_DIR, f"{arm}_seed_{seed}.json")


def archive_stats(archive):
    if not archive:
        return 0.0, 0.0, 0.0
    best = max(c["score"] for c in archive.values())
    qd = sum(c["score"] for c in archive.values())
    cov = len(archive) / (harness.GRID * harness.GRID)
    return best, qd, cov


def cmd_initall():
    if os.path.exists(CAND_LOG):
        os.remove(CAND_LOG)
    os.makedirs(STATE_DIR, exist_ok=True)
    os.makedirs(PROP_DIR, exist_ok=True)
    for arm, cfg in ARMS.items():
        for s in SEEDS:
            base = baseline_packing(cfg["W"], cfg["H"])
            ev = evaluate(base, cfg["W"], cfg["H"])
            ck = f"{harness.cell_of(ev['mean_radius'], ev['density'])}"
            st = {"arm": arm, "seed": s, "gen": 0,
                  "archive": {ck: {"score": ev["score"], "circles": base, "gen": -1}},
                  "best_circles": base, "best_score": ev["score"]}
            with open(spath(arm, s), "w") as f:
                json.dump(st, f, indent=2)
            print(f"{arm} seed {s}: baseline={ev['score']:.6f} valid={ev['valid']}")


def cmd_batchstep(arm, gen):
    cfg = ARMS[arm]
    for s in SEEDS:
        with open(spath(arm, s)) as f:
            st = json.load(f)
        if st["gen"] != gen:
            print(f"{arm} seed {s}: SKIP (state at gen {st['gen']})")
            continue
        t0 = time.time()
        pf = os.path.join(PROP_DIR, f"{arm}_seed_{s}_gen_{gen}.txt")
        raw = open(pf, encoding="utf-8", errors="replace").read() if os.path.exists(pf) else None
        circles, perr = harness.parse_proposal(raw)
        ev = evaluate(circles, cfg["W"], cfg["H"])
        row = {"arm": arm, "proposer": cfg["proposer"], "seed": s, "gen": gen,
               "parent_score": round(st["best_score"], 6), "score": round(ev["score"], 6),
               "viable": ev["viable"], "valid": ev["valid"], "n_circles": ev["n"],
               "mean_radius": round(ev["mean_radius"], 6), "density": round(ev["density"], 6),
               "parse_error": perr, "wall_s": round(time.time() - t0, 4),
               "reconstructed": False}
        with open(CAND_LOG, "a") as f:
            f.write(json.dumps(row) + "\n")
        if ev["valid"] and ev["score"] > 0:
            ck = f"{harness.cell_of(ev['mean_radius'], ev['density'])}"
            cur = st["archive"].get(ck)
            if cur is None or ev["score"] > cur["score"]:
                st["archive"][ck] = {"score": ev["score"], "circles": circles, "gen": gen}
            if ev["score"] > st["best_score"]:
                st["best_score"] = ev["score"]
                st["best_circles"] = circles
        st["gen"] = gen + 1
        with open(spath(arm, s), "w") as f:
            json.dump(st, f, indent=2)
        best, qd, cov = archive_stats(st["archive"])
        print(f"{arm} seed {s} gen {gen}: score={ev['score']:.6f} viable={ev['viable']} "
              f"valid={ev['valid']} best={best:.6f} cov={cov}")


def cmd_summary():
    out = {}
    rows = [json.loads(l) for l in open(CAND_LOG)] if os.path.exists(CAND_LOG) else []
    for arm in ARMS:
        per = []
        for s in SEEDS:
            with open(spath(arm, s)) as f:
                st = json.load(f)
            best, qd, cov = archive_stats(st["archive"])
            rs = [r for r in rows if r["arm"] == arm and r["seed"] == s]
            per.append({"seed": s, "best": round(best, 6), "qd": round(qd, 6), "cov": cov,
                        "viable": sum(1 for r in rs if r["viable"]),
                        "valid": sum(1 for r in rs if r["valid"]), "gens": len(rs)})
        out[arm] = per
    with open(RESULTS, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "initall":
        cmd_initall()
    elif c == "batchstep":
        cmd_batchstep(sys.argv[2], int(sys.argv[3]))
    elif c == "summary":
        cmd_summary()
    else:
        print("usage: harness_v2.py initall | batchstep <arm> <gen> | summary", file=sys.stderr)
        sys.exit(1)
