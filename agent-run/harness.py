#!/usr/bin/env python
"""
Real (non-reconstructed) circle-packing MAP-Elites harness for the
LLM-guided evolutionary search seed-variability / viability pilot.

The LLM (a Claude subagent) is the PROPOSER only. All scoring is done here,
deterministically, in Python. Every candidate is logged live to candidates.jsonl
at the moment it is evaluated -- there is no reconstruction.

Commands:
  init  <seed>                 create state for a seed, seed the archive with a
                               deterministic valid baseline, print the parent config
  step  <seed> <proposal_file> read a raw proposer output, parse+evaluate+log+archive,
                               print the result and the next parent config
  summary                      recompute results.json across all seeds present

Design notes (report these honestly in any paper):
  - Benchmark: pack N=26 non-overlapping circles in the unit square, maximize sum of radii.
  - viable  = the proposer output parses to exactly 26 numeric (x,y,r) triples.
  - valid   = viable AND all circles inside [0,1]^2 AND no pairwise overlap (eps tol).
  - score   = sum of radii if valid else 0.0   (invalid geometry is not rewarded)
  - archive = MAP-Elites 20x20 over (mean_radius, packing_density); QD = sum of cell bests.
  - parent selection = elitist (current archive best). Simple and deterministic given the log.
  - The Python `seed` controls parent tie-breaking / RNG only; the proposer's own sampling
    is the dominant stochastic source (and is NOT reproducible -- state this in the paper).
"""
import sys, os, json, ast, re, math, time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(HERE, "state")
CAND_LOG = os.path.join(HERE, "candidates.jsonl")
RESULTS = os.path.join(HERE, "results.json")

N = 26
EPS = 1e-6                       # overlap / boundary tolerance
GRID = 20                        # MAP-Elites resolution per descriptor
MR_RANGE = (0.0, 0.15)           # mean radius descriptor range
PD_RANGE = (0.0, 1.0)            # packing density descriptor range


# ---------- geometry / evaluation ----------

def baseline_packing():
    """Deterministic valid packing: 26 circles on a 6x5 grid, r=0.9/26. Score ~0.9."""
    r = 0.9 / N
    pts = []
    for row in range(5):
        for col in range(6):
            if len(pts) >= N:
                break
            x = (col + 0.5) / 6.0
            y = (row + 0.5) / 5.0
            pts.append([round(x, 6), round(y, 6), round(r, 6)])
    return pts


def parse_proposal(text):
    """Robustly extract a list of 26 (x,y,r) triples from raw model text.
    Returns (circles|None, parse_error|None)."""
    if text is None:
        return None, "empty"
    t = text.strip()
    # strip common markdown code fences
    t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
    t = re.sub(r"\n?```$", "", t).strip()
    candidates = []
    # 1) whole thing
    candidates.append(t)
    # 2) first balanced [...] block containing digits
    m = re.search(r"\[.*\]", t, re.DOTALL)
    if m:
        candidates.append(m.group(0))
    for c in candidates:
        try:
            obj = ast.literal_eval(c)
        except Exception:
            continue
        if not isinstance(obj, (list, tuple)):
            continue
        rows = []
        ok = True
        for item in obj:
            if not isinstance(item, (list, tuple)) or len(item) != 3:
                ok = False
                break
            try:
                x, y, r = float(item[0]), float(item[1]), float(item[2])
            except Exception:
                ok = False
                break
            rows.append((x, y, r))
        if ok and rows:
            return rows, None
    return None, "no_parse"


def evaluate(circles):
    """Return dict: viable, valid, score, mean_radius, density, n."""
    res = {"viable": False, "valid": False, "score": 0.0,
           "mean_radius": 0.0, "density": 0.0, "n": 0 if circles is None else len(circles)}
    if circles is None:
        return res
    res["n"] = len(circles)
    if len(circles) != N:
        return res            # wrong count -> not viable
    if any(r <= 0 for (_, _, r) in circles):
        return res
    res["viable"] = True      # parsed to 26 positive-radius triples
    radii = [r for (_, _, r) in circles]
    res["mean_radius"] = sum(radii) / N
    res["density"] = sum(math.pi * r * r for r in radii)  # fraction of unit square area
    # boundary check
    inside = all((x - r >= -EPS and x + r <= 1 + EPS and
                  y - r >= -EPS and y + r <= 1 + EPS) for (x, y, r) in circles)
    # overlap check
    overlap = False
    for i in range(N):
        xi, yi, ri = circles[i]
        for j in range(i + 1, N):
            xj, yj, rj = circles[j]
            d = math.hypot(xi - xj, yi - yj)
            if d + EPS < ri + rj:
                overlap = True
                break
        if overlap:
            break
    if inside and not overlap:
        res["valid"] = True
        res["score"] = sum(radii)
    return res


def cell_of(mean_radius, density):
    def b(v, lo, hi):
        if hi <= lo:
            return 0
        k = int((v - lo) / (hi - lo) * GRID)
        return max(0, min(GRID - 1, k))
    return (b(mean_radius, *MR_RANGE), b(density, *PD_RANGE))


# ---------- state ----------

def state_path(seed):
    return os.path.join(STATE_DIR, f"seed_{seed}.json")


def load_state(seed):
    with open(state_path(seed)) as f:
        return json.load(f)


def save_state(seed, st):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(state_path(seed), "w") as f:
        json.dump(st, f, indent=2)


def archive_stats(archive):
    if not archive:
        return 0.0, 0.0, 0.0
    best = max(c["score"] for c in archive.values())
    qd = sum(c["score"] for c in archive.values())
    cov = len(archive) / (GRID * GRID)
    return best, qd, cov


# ---------- commands ----------

def cmd_init(seed):
    base = baseline_packing()
    ev = evaluate(base)
    archive = {}
    ck = f"{cell_of(ev['mean_radius'], ev['density'])}"
    archive[ck] = {"score": ev["score"], "circles": base, "gen": -1}
    st = {"seed": seed, "gen": 0, "archive": archive,
          "best_circles": base, "best_score": ev["score"]}
    save_state(seed, st)
    print(json.dumps({"event": "init", "seed": seed,
                      "baseline_score": round(ev["score"], 6),
                      "parent": base}))


def cmd_step(seed, proposal_file):
    t0 = time.time()
    st = load_state(seed)
    gen = st["gen"]
    parent_score = st["best_score"]
    if proposal_file and os.path.exists(proposal_file):
        with open(proposal_file, encoding="utf-8", errors="replace") as f:
            raw = f.read()
    else:
        raw = None                     # proposer produced no file -> viability failure
    circles, perr = parse_proposal(raw)
    ev = evaluate(circles)
    wall = round(time.time() - t0, 4)

    # log row LIVE
    row = {"seed": seed, "gen": gen, "parent_score": round(parent_score, 6),
           "score": round(ev["score"], 6), "viable": ev["viable"], "valid": ev["valid"],
           "n_circles": ev["n"], "mean_radius": round(ev["mean_radius"], 6),
           "density": round(ev["density"], 6), "parse_error": perr,
           "wall_s": wall, "reconstructed": False}
    os.makedirs(HERE, exist_ok=True)
    with open(CAND_LOG, "a") as f:
        f.write(json.dumps(row) + "\n")

    # update archive if valid and improves its cell
    if ev["valid"] and ev["score"] > 0:
        ck = f"{cell_of(ev['mean_radius'], ev['density'])}"
        cur = st["archive"].get(ck)
        if cur is None or ev["score"] > cur["score"]:
            st["archive"][ck] = {"score": ev["score"], "circles": circles, "gen": gen}
        if ev["score"] > st["best_score"]:
            st["best_score"] = ev["score"]
            st["best_circles"] = circles

    st["gen"] = gen + 1
    save_state(seed, st)

    best, qd, cov = archive_stats(st["archive"])
    print(json.dumps({"event": "step", "seed": seed, "gen": gen,
                      "score": round(ev["score"], 6), "viable": ev["viable"],
                      "valid": ev["valid"], "n_circles": ev["n"], "parse_error": perr,
                      "best": round(best, 6), "qd": round(qd, 6), "cov": cov,
                      "next_parent": st["best_circles"]}))


def cmd_summary():
    rows = []
    if not os.path.isdir(STATE_DIR):
        print("[]"); return
    for fn in sorted(os.listdir(STATE_DIR)):
        if not fn.startswith("seed_"):
            continue
        st = json.load(open(os.path.join(STATE_DIR, fn)))
        seed = st["seed"]
        best, qd, cov = archive_stats(st["archive"])
        # count viability from the live log
        viable = total = 0
        if os.path.exists(CAND_LOG):
            for line in open(CAND_LOG):
                r = json.loads(line)
                if r["seed"] == seed:
                    total += 1
                    viable += 1 if r["viable"] else 0
        rows.append({"seed": seed, "best": round(best, 6), "qd": round(qd, 6),
                     "cov": cov, "viable": viable, "gens": total})
    with open(RESULTS, "w") as f:
        json.dump(rows, f, indent=2)
    print(json.dumps(rows))


SEEDS = [42, 123, 456, 789, 1111]
PROP_DIR = os.path.join(HERE, "prop")


def cmd_initall():
    # fresh run: clear the live log so the sweep starts clean
    if os.path.exists(CAND_LOG):
        os.remove(CAND_LOG)
    os.makedirs(PROP_DIR, exist_ok=True)
    for s in SEEDS:
        cmd_init(s)


def cmd_batchstep(gen):
    """Step every seed for one generation, reading prop/seed_<S>_gen_<gen>.txt.
    Missing/garbage files become viability failures (real, not reconstructed)."""
    out = []
    for s in SEEDS:
        st = load_state(s)
        if st["gen"] != gen:
            out.append({"seed": s, "skipped": True, "state_gen": st["gen"]})
            continue
        pf = os.path.join(PROP_DIR, f"seed_{s}_gen_{gen}.txt")
        # capture printed step result
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_step(s, pf)
        out.append(json.loads(buf.getvalue().strip().splitlines()[-1]))
    for o in out:
        if o.get("skipped"):
            print(f"seed {o['seed']}: SKIP (state at gen {o['state_gen']})")
        else:
            print(f"seed {o['seed']} gen {o['gen']}: score={o['score']} "
                  f"viable={o['viable']} valid={o['valid']} best={o['best']} cov={o['cov']}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "init":
        cmd_init(int(sys.argv[2]))
    elif cmd == "initall":
        cmd_initall()
    elif cmd == "step":
        cmd_step(int(sys.argv[2]), sys.argv[3])
    elif cmd == "batchstep":
        cmd_batchstep(int(sys.argv[2]))
    elif cmd == "summary":
        cmd_summary()
    else:
        print("usage: harness.py initall | init <seed> | step <seed> <file> | "
              "batchstep <gen> | summary", file=sys.stderr)
        sys.exit(1)
