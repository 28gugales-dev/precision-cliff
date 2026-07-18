# 14B precision sweep — provenance note

**Run:** 2026-07-17/18, Kaggle 2x Tesla T4, `kaggle_precision_sweep_14b.py`
(same script as `kaggle_precision_sweep.py` with REPO=Qwen/Qwen2.5-Coder-14B-Instruct-GGUF,
4-rung ladder q8_0/q4_k_m/q3_k_m/q2_k — no fp16, does not fit 2xT4 — and
WORK=/kaggle/working/precision_sweep_14b). 4 x (5 seeds x 10 gens + 6 probes) = 224 generations.

**Data status — IMPORTANT:**
- The run completed to `[done]`, but the Kaggle session expired before the output
  folder was downloaded; `/kaggle/working` was wiped. The per-candidate jsonl,
  probe raws, state checkpoints, and full sha256 digests are LOST.
- `precision_sweep_14b_console.log` is the VERBATIM console output of the run
  (per-candidate lines printed live at evaluation time), preserved in the owner's
  Kaggle notebook via Quick Save (version history) and copied here. It is a real
  live log, NOT a reconstruction. sha256 prefixes for all four GGUF files appear
  in it (8180f66e…, c1e65973…, 93b69ebf…, 4542a8bb…).
- Per project integrity rules, nothing in this log may be back-filled into jsonl
  form. Any paper claim from this run must cite the console log and disclose the
  file loss. Fields never printed (n_circles, parse_error, raw text) are simply
  unavailable; parent-echo is inferred from score identity with the lineage's
  RUNNING parent (the seed's best after the previous gen), not verified against
  raw coordinates. NOTE 2026-07-18: the first version of stats_precision_14b.py
  compared scores to the hardcoded 0.89999 baseline only, undercounting echoes
  of later parents on the upper rungs (3/57 reported; true 12/57). Caught in
  review; corrected. Current numbers: q2_k 17/18 vs others 12/57, Fisher
  p=2.5e-8. The legacy baseline-only counts are retained in the results json
  under legacy_baseline_only_echo_counts.

**Analysis:** `stats_precision_14b.py` parses the console log directly and
recomputes all aggregates; output `results_precision_14b_local.json`.
