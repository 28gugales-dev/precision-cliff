# Best-of-50 zero-shot control + direct knowledge probes — provenance

**Run:** 2026-07-18, orchestrated locally (Claude Code session), in response to external
review demanding the best-of-N control ("the single most important addition").

## Best-of-50 zero-shot control (`probe50/`, `probes_bestof50.jsonl`)

- 50 independent zero-shot invocations per condition: `claude-haiku` and `claude-sonnet`
  (same undated aliases as Arms A-D; agent-runtime default sampling; NOT the original
  probe protocol — these agents reply with the raw list directly instead of writing a
  file. Disclosed in paper §5.5).
- Prompt: fixed verbatim across all 100 invocations (task statement + constraints +
  no-tools/no-code rule + raw-list-only output). Stored in paper Appendix.
- Each agent's final output saved VERBATIM to `probe50/{haiku,sonnet}_zs_NN.txt` at
  receipt; scored by `score_probe50.py` (same evaluator rules as harness.py, EPS=1e-6);
  one jsonl row per file appended at evaluation time, `reconstructed:false`.
- RESULTS: haiku 49/50 viable, 45/50 valid, best 2.541421, 28 valid outputs within
  5e-4 of the 2.5414 attractor, 0 above it. sonnet 50/50 valid, best 2.541421,
  29 near-attractor, 0 above. Best-of-50 zero-shot == loop ceiling exactly, both tiers.
- One structural outlier: sonnet_zs_44 (central r=0.5 circle + Apollonian corner fill)
  — valid, scores below the grid template.

## Direct knowledge probes (`probe_knowledge/`)

- 3 haiku + 3 sonnet, one fixed question: best known value/configuration for max
  sum-of-radii, N=26, unit square; instructed to say plainly if unknown.
- RESULT: 6/6 disclaim knowledge of any published value for this objective;
  1/6 (sonnet_k2) recalls that Erich Friedman's "Circles in Squares" catalog covers
  the objective but cannot recall values; 0/6 name 2.635862 or any catalogued number.
- Responses saved verbatim at receipt.

## Integrity

Same rules as the rest of the corpus: outputs archived verbatim before scoring,
never back-filled, deterministic evaluator, no LLM self-scoring.
