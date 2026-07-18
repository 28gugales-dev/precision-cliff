#!/usr/bin/env python
"""
Arm D — program evolution. The proposer (Claude Haiku, Read/Write tools only,
no execution) writes a PYTHON PROGRAM; this harness executes it sandboxed and
scores its output with the same deterministic evaluator as arms A-C.

Contract for proposed programs (prop_v3/prog_seed_<s>_gen_<g>.py):
  - imports restricted to: math, random, itertools, functools (AST-checked)
  - must print exactly one line to stdout: Python list of 26 [x, y, r] floats
  - killed after 30 s wall time
  - names open/exec/eval/__import__/compile/input are banned (AST-checked)

Failure taxonomy logged per candidate in exec_error:
  banned_import | banned_name | syntax_error | timeout | crash | no_output |
  parse_error | None (ran clean)

Same live-logging discipline: every candidate appended to candidates_v3.jsonl
at evaluation time with reconstructed:false. Rows are never back-filled.

Commands:
  initall                 init 5 seeds (baseline = harness.baseline_packing, 0.89999)
  batchstep <gen>         execute + evaluate prop_v3/prog_seed_<s>_gen_<gen>.py for all seeds
  summary                 write results_v3.json
"""
import sys, os, json, math, time, ast, subprocess
import harness            # parse_proposal, cell_of, N, EPS, GRID, baseline_packing
import harness_v2         # evaluate(circles, W, H)

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(HERE, "state_v3")
PROP_DIR = os.path.join(HERE, "prop_v3")
CAND_LOG = os.path.join(HERE, "candidates_v3.jsonl")
RESULTS = os.path.join(HERE, "results_v3.json")

SEEDS = [42, 123, 456, 789, 1111]
ARM = "prog_haiku"
PROPOSER = "claude-haiku"
TIMEOUT_S = 30
ALLOWED_IMPORTS = {"math", "random", "itertools", "functools"}
BANNED_NAMES = {"open", "exec", "eval", "__import__", "compile", "input",
                "os", "sys", "subprocess", "socket", "importlib", "builtins"}


def ast_check(src):
    """Return None if program passes the sandbox allowlist, else failure tag."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return "syntax_error"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS:
                    return "banned_import"
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                return "banned_import"
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            return "banned_name"
        elif isinstance(node, ast.Attribute) and node.attr in BANNED_NAMES:
            return "banned_name"
    return None


def run_program(path):
    """Execute proposed program sandboxed. Returns (stdout_text, exec_error, wall_s)."""
    src = open(path, encoding="utf-8", errors="replace").read()
    tag = ast_check(src)
    if tag:
        return None, tag, 0.0
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, "-I", path], capture_output=True,
                           timeout=TIMEOUT_S, cwd=PROP_DIR)
    except subprocess.TimeoutExpired:
        return None, "timeout", round(time.time() - t0, 3)
    wall = round(time.time() - t0, 3)
    out = p.stdout.decode("utf-8", errors="replace")
    if p.returncode != 0:
        return None, "crash", wall
    if not out.strip():
        return None, "no_output", wall
    return out, None, wall


def spath(seed):
    return os.path.join(STATE_DIR, f"prog_seed_{seed}.json")


def cpath(seed):
    return os.path.join(STATE_DIR, f"ctx_prog_seed_{seed}.txt")


def write_ctx(seed, st):
    """Context file the proposer agent reads: score to beat + champion program."""
    lines = [f"GENERATION: {st['gen']}",
             f"SCORE TO BEAT (sum of 26 radii, current best): {st['best_score']:.6f}",
             f"KNOWN OPTIMUM FOR THIS PROBLEM: not told. Higher score = better.",
             ""]
    if st.get("best_program"):
        lines += ["CURRENT CHAMPION PROGRAM (produced the best score above):",
                  "----------------------------------------", st["best_program"],
                  "----------------------------------------"]
    else:
        lines += ["No champion program yet. The best-so-far packing came from a",
                  "fixed baseline (26 equal circles on a 6x5 grid, r=0.034615).",
                  "Write the first program from scratch."]
    with open(cpath(seed), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


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
    for s in SEEDS:
        base = harness.baseline_packing()
        ev = harness_v2.evaluate(base, 1.0, 1.0)
        ck = f"{harness.cell_of(ev['mean_radius'], ev['density'])}"
        st = {"arm": ARM, "seed": s, "gen": 0,
              "archive": {ck: {"score": ev["score"], "gen": -1}},
              "best_score": ev["score"], "best_program": None}
        with open(spath(s), "w") as f:
            json.dump(st, f, indent=2)
        write_ctx(s, st)
        print(f"{ARM} seed {s}: baseline={ev['score']:.6f} valid={ev['valid']}")


def cmd_batchstep(gen):
    for s in SEEDS:
        with open(spath(s)) as f:
            st = json.load(f)
        if st["gen"] != gen:
            print(f"seed {s}: SKIP (state at gen {st['gen']})")
            continue
        pf = os.path.join(PROP_DIR, f"prog_seed_{s}_gen_{gen}.py")
        if os.path.exists(pf):
            out, exec_err, wall = run_program(pf)
        else:
            out, exec_err, wall = None, "missing_file", 0.0
        circles, perr = harness.parse_proposal(out) if out else (None, exec_err)
        if out and circles is None and exec_err is None:
            exec_err = "parse_error"
        ev = harness_v2.evaluate(circles, 1.0, 1.0)
        row = {"arm": ARM, "proposer": PROPOSER, "seed": s, "gen": gen,
               "parent_score": round(st["best_score"], 6), "score": round(ev["score"], 6),
               "viable": ev["viable"], "valid": ev["valid"], "n_circles": ev["n"],
               "mean_radius": round(ev["mean_radius"], 6), "density": round(ev["density"], 6),
               "exec_error": exec_err, "exec_wall_s": wall,
               "reconstructed": False}
        with open(CAND_LOG, "a") as f:
            f.write(json.dumps(row) + "\n")
        if ev["valid"] and ev["score"] > 0:
            ck = f"{harness.cell_of(ev['mean_radius'], ev['density'])}"
            cur = st["archive"].get(ck)
            if cur is None or ev["score"] > cur["score"]:
                st["archive"][ck] = {"score": ev["score"], "gen": gen}
            if ev["score"] > st["best_score"]:
                st["best_score"] = ev["score"]
                st["best_program"] = open(pf, encoding="utf-8", errors="replace").read()
        st["gen"] = gen + 1
        with open(spath(s), "w") as f:
            json.dump(st, f, indent=2)
        write_ctx(s, st)
        best, qd, cov = archive_stats(st["archive"])
        print(f"seed {s} gen {gen}: score={ev['score']:.6f} viable={ev['viable']} "
              f"valid={ev['valid']} err={exec_err} best={best:.6f}")


def cmd_summary():
    rows = [json.loads(l) for l in open(CAND_LOG)] if os.path.exists(CAND_LOG) else []
    per = []
    for s in SEEDS:
        with open(spath(s)) as f:
            st = json.load(f)
        best, qd, cov = archive_stats(st["archive"])
        rs = [r for r in rows if r["seed"] == s]
        per.append({"seed": s, "best": round(best, 6), "qd": round(qd, 6), "cov": cov,
                    "viable": sum(1 for r in rs if r["viable"]),
                    "valid": sum(1 for r in rs if r["valid"]),
                    "errors": {e: sum(1 for r in rs if r["exec_error"] == e)
                               for e in set(r["exec_error"] for r in rs if r["exec_error"])},
                    "gens": len(rs)})
    out = {ARM: per}
    with open(RESULTS, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "initall":
        cmd_initall()
    elif c == "batchstep":
        cmd_batchstep(int(sys.argv[2]))
    elif c == "summary":
        cmd_summary()
    else:
        print("usage: harness_v3.py initall | batchstep <gen> | summary", file=sys.stderr)
        sys.exit(1)
