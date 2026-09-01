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

(To be filled after data collection.)
