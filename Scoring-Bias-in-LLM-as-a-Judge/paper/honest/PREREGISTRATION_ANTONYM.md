# Antonym Probe Preregistration

**Registered:** 2026-09-01, before any sampling.
**Authors:** Sricharan Samba, Soham Gugale

## Design

The antonym probe extends the scoring-bias study with a sixth bias family that
tests whether LLM judges are sensitive to the semantic content of rubric
descriptors or anchor on positional/numeric cues.

**Unit of analysis:** model family (base vs instruct pair). Same 13 families,
same 50 items, same logit-scoring protocol as the main panel.

**Metric:** Delta = max inter-variant spread in mean expected-value score, same
definition as the main panel.

**Variants (3):**
- `standard`: "as one of: Poor, Fair, Good, Great, Excellent" (ascending quality)
- `replaced`: "as one of: Terrible, Weak, Average, Strong, Outstanding" (same
  ascending direction, different antonym word tokens)
- `flipped`: "as one of: Outstanding, Strong, Average, Weak, Terrible" (reversed
  semantic direction, position 1 = positive word, position 5 = negative word)

The `standard` variant is identical to `score_id: descriptive` from the main
panel and serves as the shared control.

## Confirmatory predictions

**PA1 (token sensitivity):** The `replaced` variant produces a different mean
expected-value score than `standard` in at least 8/13 families (pooled across
base+instruct). Different rubric words with the same ordinal meaning should
still shift the logit distribution because the model attends to token identity,
not just scale direction.

**PA2 (semantic-conflict effect):** The `flipped` variant produces a larger
absolute shift from `standard` than `replaced` does, in at least 8/13 families.
The semantic-numeric conflict (positive word at position 1, negative at
position 5) is a stronger perturbation than mere token replacement.

**PA3 (instruct amplification):** The instruct delta (max-min spread across the
3 antonym variants) exceeds the base delta in more families than not
(sign count > 6/13). This extends the main panel's finding that instruction
tuning increases scoring bias to the antonym manipulation.

**PA4 (conflict sensitivity):** Instruct models show a larger absolute shift
under the `flipped` condition than base models do (paired Wilcoxon on
|flipped - standard|, p < 0.05). If tuning installs responsiveness to rubric
semantics, the semantic-numeric conflict should hit instruct judges harder.

## Decision rule

PA1 and PA2 are descriptive counts. PA3 and PA4 are tested with paired Wilcoxon
signed-rank. No Holm correction is applied (these are pre-specified, not
exploratory). A refuted prediction is reported as refuted with the observed
counts.

## Outcomes

**Interim outcomes (recorded 2026-09-03; 10 of the 13 registered families).**
The three 7B to 8B families (Qwen2.5-7B, OLMo-2-7B, Granite-3.1-8B) have not
been run: they need a GPU, and the data below came from a CPU replication
(`repro/cpu_rerun.py`, fp32 up to 0.5B and bfloat16 above, recorded per
checkpoint in `repro/results_scaled_cpu_rerun.json`). The registered
thresholds were written for 13 families; the counts below are reported
against 10 and the final verdicts wait for the full panel. Analysis:
`repro/analyze_antonym.py results_scaled_cpu_rerun.json` →
`repro/results_antonym_analysis.json`.

- **PA1 (token sensitivity): met, 10/10.** Every family's pooled mean under
  `replaced` differs from `standard` by more than 0.05; the mean shift is
  +0.54 (base) and +0.72 (instruct). The synonym set is not neutral: judges
  put more mass on "Strong" and "Outstanding" than on "Great" and
  "Excellent" with the same numeric mapping.
- **PA2 (semantic conflict beats token replacement): not met, 5/10.** The
  `flipped` shift is larger than the `replaced` shift in half the families.
  Direction of the `flipped` shift is negative in both arms (base −0.59,
  instruct −0.62), so judges do follow the word rather than the position;
  the effect is just not larger than the token-replacement effect.
- **PA3 (instruct amplification): not met, 5/10.** Instruct delta exceeds
  base delta in 5 families (mean change +0.28, bootstrap 95% CI
  [−0.20, 0.81], Wilcoxon p = 0.49, dz = 0.35). Qwen2.5-3B goes the other
  way strongly (1.12 → 0.26); Falcon3-1B and StableLM-2-1.6B go up strongly
  (+1.79, +1.48).
- **PA4 (conflict sensitivity): not met, 6/10, Wilcoxon p = 0.63.**

Net reading at 10 families: the antonym manipulation is a large bias (mean
delta 1.36 base, 1.64 instruct, larger than any of the five original probes)
that is driven mainly by token identity, and instruction tuning does not
amplify it consistently. This is the first probe in the project where the
tuning effect is not directionally positive, and it is worth reporting as
such once the three large families are in.
