# When the Loop Is Inert: Viability and Recall in LLM-Guided Circle Packing

Code, raw per-candidate data, and paper for a controlled study of LLM-guided
evolutionary search on circle packing (N=26 unit square, maximize sum of radii),
including:

- **Four proposer arms** (Haiku pilot, Sonnet, non-templated rectangle, program
  evolution) plus best-of-50 and knowledge-probe controls: the loop's apparent
  progress is selection over a zero-shot-constructible attractor packing
  (2.541421), not search.
- **Two quantization ladders** (Qwen2.5-Coder 7B and 14B, GGUF q2_k → q8_0/fp16):
  viability is flat across precision at both scales; at 14B a **novelty cliff**
  appears between 3.91 and 3.35 bits per weight — at q2_k the model keeps format
  and geometry but almost every valid proposal is a verbatim, coordinate-identical
  copy of its parent (17/18 vs 2–3/20 at upper rungs).
- **Fresh-seed replication + must-differ mechanism probe** (in progress at first
  commit; data lands in `agent-run/precision_sweep_14b_fresh/` when the batch
  kernel completes) and an **N-generality arm** (N=23/27, `agent-run/*_v4*`).

## Layout

| Path | Contents |
|---|---|
| `paper/` | Paper (markdown canonical + PDF) |
| `agent-run/harness.py`, `harness_v2.py`, `harness_v3.py`, `harness_v4.py` | Deterministic evaluator/logging harnesses (pilot, arms B–C, program evolution, N-generality) |
| `agent-run/kaggle_precision_sweep*.py` | Self-contained resumable Kaggle runners (7B ladder, 14B ladder, 14B durable re-execution, 14B fresh-seed + must-differ) |
| `agent-run/candidates*.jsonl` | Per-candidate live logs (every row `reconstructed: false`) |
| `agent-run/precision_sweep/`, `precision_sweep_14b_v2_output/` | Sweep outputs: jsonl, checkpoints, sha256-pinned provenance |
| `agent-run/precision_sweep_14b_console.log` + `precision_sweep_14b_README.md` | Verbatim console log of the original 14B run (per-candidate files lost to session expiry; provenance rules in the README) |
| `agent-run/probe50/`, `probe_knowledge/`, `probe*/` | Best-of-50 zero-shot controls and knowledge probes |
| `agent-run/stats_*.py`, `score_probe50.py`, `results*.json` | Statistics scripts and their outputs — every number in the paper recomputes from the jsonl |
| `agent-run/figures/` + `make_fig*.py` | All paper figures + generators |
| `agent-run/prop*/`, `state*/` | Raw proposer outputs and lineage checkpoints |

## Reproducing the numbers

Each stats script reads only the jsonl/log artifacts and rewrites its
`results_*.json`; e.g.:

```bash
python agent-run/stats_precision_14b_v2.py agent-run/precision_sweep_14b_v2_output/precision_sweep_14b
```

The Kaggle runners are self-contained (bootstrap header installs
`llama-cpp-python` cu122 wheel), resume from checkpoints, echo every jsonl row
to the console with a `JSONL|` prefix, and sha256-pin the GGUF weights they use.

## Data integrity conventions

- Every logged candidate row carries `reconstructed: false`; no log line is ever
  back-filled or regenerated after the fact.
- The one data-loss event (original 14B run) is disclosed in the paper and in
  `precision_sweep_14b_README.md`; its surviving console log is archived
  verbatim and was later superseded by a coordinate-logged bit-identical
  re-execution (`precision_sweep_14b_v2_output/`).
- Preregistered prediction blocks are baked into the Kaggle runner headers and
  timestamped by Kaggle version history before execution; the harness_v4 header
  hypotheses are timestamped by this repository's first commit.

## License

MIT (see `LICENSE`). If you use this data or code, please cite the paper in
`paper/`.
