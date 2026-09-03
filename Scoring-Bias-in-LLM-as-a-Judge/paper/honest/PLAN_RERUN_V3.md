# Plan: rerun the scoring-bias experiment, better

Status: design draft, 2026-09-02. Nothing here has been run. Written before any
new data so it can serve as the preregistration base for a v3 study.

## 1. Goal

Rerun the exact question of the paper ("does instruction tuning make an LLM judge
more biased, and is confidence an inverted screen for bias?") with a design that
closes the gaps the paper itself reports in its Limitations, and then extend it
with the antonym probe and a few new probes that the current design cannot ask.

Same core protocol (logit readout of the score distribution, base vs instruct
pairs, nuisance perturbations, delta metric), fixed where the paper shows it is
fragile.

## 2. What the current design is

- 13 open-weight families, 0.1 to 8B, base + instruct = 26 checkpoints.
- 50 hand-written items, 5 domains x 10, one short response each.
- 5 bias types (rubric order, score ID, reference answer, authority, verbosity),
  3 variants each. Antonym is a 6th, not yet run.
- One prompt template, raw completion format for every checkpoint.
- Score = expected value over the 5 answer tokens at the position right after
  "### Score:". Delta = max minus min of variant means.
- Stats: paired Wilcoxon per probe, Holm across probes, bootstrap CIs, exact
  sign-flip permutation, family-clustered OLS. Unit is the family, n = 13.
- Ground truth: 20 gold good/bad pairs.
- Mechanism: activation patching (2 families), span patching, attention null.
- fp16 on a Kaggle P100, transformers 4.49.

## 3. Where it is weak (each point is tied to something the paper reports)

W1. **Power.** n = 13 families and no within-model variance. The headline H0
    does not survive Holm (smallest adjusted p = 0.133). The out-of-sample
    predictor R2 CI spans zero. The paper leans on effect sizes and a
    permutation test because it has to.

W2. **Items.** 50 items, all one-sentence factual answers. 49 of 50 responses
    are a single sentence, so the "terse" verbosity variant is a no-op on 49
    items (Limitation 7). No quality variation across responses, so bias vs
    true quality cannot be studied. All five domains are short Q&A; no code,
    no math with wrong steps, no long-form writing.

W3. **Template.** One template in the main panel. P15 shows the instruct > base
    direction holds in only 6 of 10 templates on the smallest models. The paper
    calls the relation robust to wording, but the direction of the tuning effect
    is not, at least at small scale.

W4. **Readout position.** The answer-token mass at the scored position is tiny
    (mean 0.15%, instruct 0.03%). P18 shows the real numeric mass (0.91 to 0.96)
    sits one token later, after the space. The paper scores the low-mass
    position and shows it correlates with the high-mass one at rho = 0.79. Better
    to score the high-mass position directly and report both.

W5. **Chat format.** Instruct checkpoints are scored in raw completion format,
    which is out of distribution for them. P19 tested chat templates on only
    3 families (n = 6 cells, p = 0.33). The confound is only partly closed.

W6. **Perturbation construction.** Each variant is one fixed string. Authority
    has one "expert" phrasing and one "novice" phrasing. Verbosity uses one
    fixed filler. Any lexical quirk of that one string is confounded with the
    probe. The "random" rubric variant is a single odd mapping.

W7. **Delta metric.** max minus min across 3 variants is biased upward by noise
    and hides direction. Two probes with the same delta can have opposite signs.

W8. **Ground truth.** 20 gold pairs, hand-written. Wilcoxon at n = 5 families
    bottoms out at p = 0.0625. The reversed-rubric condition is ambiguous
    (Limitation 6).

W9. **Scale.** Stops at 8B, 14B only at 4-bit. Frontier only through 3 logprob
    judges, and there the frontier judges were the most biased (P20c failed).
    Whether bias attenuates with scale within a family is not tested with a
    full ladder.

W10. **Tuning recipe.** Base vs instruct differs in many things at once (data,
    SFT, DPO, RLHF, sometimes extra pretraining). The stage ablation (OLMo-2,
    Tulu-3) is the right idea but covers 3 ladders.

W11. **Mechanism.** Attention null uses raw attention mass (Limitation 9).
    Patching is on 2 families. The decisiveness x responsiveness product
    predicts the per-cell direction 74% of the time, which is good but leaves
    26% unexplained.

W12. **Reproducibility of numbers.** fp16 on one GPU type. CI demands exact
    numerical match, which no rerun on different hardware will satisfy.

W13. **Only absolute scoring.** Real judge use is mostly pairwise. Position
    bias, the most cited judge bias, is not in the suite.

## 4. The improved design

### 4.1 Items (fixes W2, W8)

- **N = 300 items**, not 50. Two sources:
  - 200 from a public instruction set with human quality labels (HelpSteer2 has
    per-response 0 to 4 helpfulness scores; use it so every response carries a
    human score). Stratify over 5 task types: factual QA, reasoning/math,
    coding, summarization, open-ended writing.
  - 100 kept from the current 50 plus the Dolly-15k replication set, so the
    v2 numbers can be compared directly on the shared subset.
- **Two responses per prompt** where the source has them, one high-quality and
  one low-quality by human label. This gives 200+ gold pairs for free (vs 20)
  and lets us test bias x quality interaction.
- Response length distribution: median 3 to 5 sentences, so terse actually
  truncates and verbose padding is a real ratio, not a constant.

### 4.2 Judges (fixes W1, W9, W10)

- **Target 24 to 28 families**, each a public base + instruct pair. Candidates
  beyond the current 13 (all have open base + instruct, all fit a T4 at bf16 or
  4-bit): Llama-3.2-1B/3B, Llama-3.1-8B, Gemma-2-2B/9B, Gemma-3-1B/4B,
  Phi-3.5-mini, Mistral-7B-v0.3, Yi-1.5-6B/9B, InternLM2.5-1.8B/7B,
  DeepSeek-LLM-7B, TinyLlama-1.1B, Pythia (via Dolly tunes), OLMo-2-1B/13B,
  MobileLLM.
- **Two full size ladders** inside one family: Qwen2.5 (0.5, 1.5, 3, 7, 14, 32B)
  and Llama-3.x (1, 3, 8, 70B). 32B and 70B in 4-bit on a Kaggle T4x2 or a
  single rented A100 hour. This turns "attenuates with scale" into a
  within-family slope instead of a between-family scatter.
- **Recipe ladders** (extends the stage ablation): OLMo-2 1B/7B/13B (base, SFT,
  DPO, RLVR all public), Tulu-3 8B, SmolLM2 (SFT-only vs SFT+DPO both public),
  Zephyr-7B (SFT vs DPO). That is 6 ladders, ~20 stage checkpoints.
- **Frontier**: any judge with logprobs. gpt-4o, gpt-4o-mini, gpt-4.1,
  Llama-3.1-70B/405B, DeepSeek-V3, Qwen2.5-72B via a provider that exposes
  logprobs. Budget well under US$20 at 300 items x ~20 variants.

### 4.3 Probes (fixes W6, W13, adds antonym properly)

Keep the 5 original probes so v2 and v3 are comparable, and fix construction:

- **Every variant gets 3 surface phrasings**, sampled per item. "Expert" is
  three different expert sentences, "novice" three different novice sentences.
  Verbosity uses three filler styles (restatement, hedging, generic
  elaboration) at a fixed token ratio (1.5x and 2.5x), not one string.
  The measured effect is then the mean over phrasings, and phrasing variance is
  reported.
- **Antonym probe, four-arm version.** The 3-arm design (standard / replaced /
  flipped) cannot separate "token identity" from "semantic direction" from
  "position". Add a fourth arm and a second synonym set:
  - `numeric`: 1 to 5 (position only; shared control with score_id)
  - `nonsense`: five made-up labels ("Zorb, Plim, Trask, Velt, Quon") in
    ascending position (position + arbitrary tokens, no semantics)
  - `standard`: Poor..Excellent
  - `synonym_A`: Terrible..Outstanding (same direction, different tokens)
  - `synonym_B`: Bad..Superb (second synonym set, to show it is not one word)
  - `flipped`: Outstanding..Terrible (semantics conflict with position)
  Predictions: nonsense ~ numeric (position dominates) vs nonsense != numeric
  (tokens matter even without meaning); flipped shift >> synonym shift
  (semantics matter). This is the cleanest test of the "token vs meaning"
  question and it is cheap: 6 variants x 300 items.
- **Pairwise probe (new).** Same items, two responses, "which is better, A or
  B". Variants: original order, swapped order. Position bias delta from the
  swap. This connects the confidence-bias law to the most studied judge bias
  and tests whether it holds under a two-token readout (A vs B).
- **Sycophancy** stays (it was the largest effect in v2). Anchoring is dropped
  to a secondary probe (it was a clean null).

### 4.4 Readout and format (fixes W4, W5)

- Score at **both** positions: the bare-token position (v2 protocol, for
  comparability) and the high-mass position after the space token (P18). The
  high-mass readout is primary in v3.
- Every instruct checkpoint is scored in **both** raw completion format and its
  own chat template. Chat is primary for instruct; raw is the comparability arm.
  Base checkpoints are raw only (they have no chat template).
- Record the full 5-way probability vector and the total mass at both
  positions for every item, as v2 does, so any readout can be recomputed
  offline without rerunning models.

### 4.5 Templates (fixes W3)

- **5 templates** in the main panel, not 1. Take the 3 from the v2 template
  study plus 2 from the 10-template study that differed most in structure
  (one with a system-style preamble, one with the rubric after the response).
- Template is a crossed random effect in the model. Report the tuning effect
  marginal over templates, and the per-template range.

### 4.6 Metric (fixes W7)

Report three things per family x probe x checkpoint:
- **Signed shift** of each non-control variant from control, with an item-level
  bootstrap CI (items are the resampling unit).
- **Delta** = max minus min, as v2, for comparability only.
- **Responsiveness** = mean total-variation distance of the 5-way distribution
  between control and variant, and **decisiveness** = 1 minus normalized
  entropy of the control distribution. These are the two terms of the paper's
  Prop 1 and should be primary, since the theory is about them.

### 4.7 Statistics (fixes W1)

- One primary model instead of dozens of Wilcoxons: a hierarchical model
  `shift ~ checkpoint_type * probe + (1 | family) + (1 | item) + (1 | template)`
  fit with statsmodels mixed LM, plus a Bayesian version (PyMC or bambi) for
  the posterior of the tuning effect. Family-clustered bootstrap as the
  robustness check.
- Preregister **three** primary hypotheses only (see section 6). Everything
  else is secondary and reported without a significance claim.
- Power: with ~25 families and 300 items the family-level paired test has
  >0.8 power for a standardized effect of 0.6, which is below the v2 point
  estimate (d_z ~ 1.0 for most probes). v2 at n = 13 had ~0.5 power at that
  effect.

### 4.8 Mechanism (fixes W11)

- **Attribution patching** (gradient-based, cheap) across every family up to
  3B, instead of full activation patching on 2 families. Gives a per-layer
  per-family localization map for the tuning shift.
- **Logit lens on the score token** across layers, control vs nuisance, to see
  at which layer the nuisance first moves the score distribution. This is a
  direct picture of "encoded, not attended".
- **Linear probe** on the nuisance-span residual for "expert vs novice": if
  instruct models encode the framing more linearly, that is the mechanism the
  paper's span-patching result implies.
- Keep the decisiveness x responsiveness cell prediction, and report it as a
  held-out prediction: fit on half the families, predict the other half.

### 4.9 Reproducibility (fixes W12)

- Run everything in **bf16** on a fixed transformers version. Commit per-item
  probability vectors, not just means.
- CI checks numbers to a **stated tolerance** (1e-3 on means) rather than
  exact match, and documents which hardware produced the committed file.
- One config file drives every harness (items, probes, templates, judges), so
  the paper's tables can be regenerated from the config plus the raw file.

## 5. Compute plan

| Phase | What | Where | Cost | Wall time |
|---|---|---|---|---|
| 0 | Smoke: 2 families, 20 items, all probes, both readouts, both formats | this CPU box (4 cores, 15GB, has AMX bf16) | 0 | 1 hour |
| 1 | All families <= 3B (about 16 families x 2 checkpoints), full design | this CPU box, background, bf16 | 0 | 2 to 4 days |
| 2 | 7B to 14B families and the recipe ladders | Kaggle T4 x2, free tier (~30 GPU-h/week) | 0 | 1 to 2 weeks of quota |
| 3 | 32B, 70B ladders at 4-bit | Kaggle T4 x2 or 2 to 3 rented A100 hours | 0 to ~US$10 | 1 day |
| 4 | Frontier logprob judges | API | < US$20 | hours |
| 5 | Mechanism (attribution patching, logit lens, probes) on <= 3B | this CPU box | 0 | 2 days |

Forward-pass budget for phase 1: 300 items x ~40 variants (5 probes x 3
variants x 3 phrasings, antonym 6, pairwise 2, sycophancy 3) x 5 templates x 2
formats is about 100k passes per checkpoint at the full crossing. That is too
many on CPU for the 3B models. So: run the **full crossing on 100 items** and
the **primary template + primary format on all 300**. That is ~30k passes per
checkpoint, ~1 second each at 1.5B on this box, ~4 seconds at 3B. Fine in the
background.

## 6. Preregistered primary hypotheses (v3)

H1. **Tuning raises bias.** Marginal over probes, templates and readouts, the
    instruct checkpoint's mean signed |shift| exceeds the base checkpoint's,
    posterior P(effect > 0) > 0.95 in the hierarchical model, and the family
    sign count is > 50%.

H2. **Confidence is an inverted screen.** Across all checkpoints, control-
    condition entropy correlates negatively with mean |shift| (Spearman < 0,
    p < 0.01), and the sign holds within base-only and within instruct-only.

H3. **Antonym: meaning beats token.** |flipped minus standard| >
    |synonym minus standard| in more than 50% of families, and nonsense labels
    sit closer to numeric than to standard (position dominates when there is
    no meaning to conflict with).

Secondary (reported, not powered): within-ladder scale slope; chat vs raw
agreement; pairwise position bias following the same entropy law; recipe stage
of onset replicating P7; template variance of the tuning effect.

## 7. What this buys over v2

| v2 weakness | v3 change | What it changes in the paper |
|---|---|---|
| n = 13, Holm fails | ~25 families, 300 items, one hierarchical model | Headline claim gets a real p and a posterior |
| terse is a no-op | multi-sentence responses | Verbosity becomes a two-sided probe |
| one template | 5 crossed templates | Tuning effect is marginal over wording, answers P15(b) |
| low-mass readout | high-mass primary, bare secondary | Removes the biggest reviewer objection |
| raw format for instruct | chat primary | Removes the OOD-format objection |
| one string per variant | 3 phrasings per variant | Separates the probe from its wording |
| max minus min | signed shift + TV responsiveness | Theory terms become the measured quantities |
| 20 gold pairs | 200+ human-labelled pairs | Discrimination loss is testable at n = 200 |
| 3-arm antonym | 6-arm antonym with nonsense control | Token vs meaning vs position is decided |
| no pairwise | pairwise swap probe | Connects to position bias literature |
| 2-family patching | attribution patching on all <= 3B | Mechanism claim generalizes |
| exact-match CI | tolerance CI, bf16 | Anyone can rerun and pass |

## 8. Order of work

1. Freeze this plan, register H1 to H3 with a dated commit (this file).
2. Build the item set (HelpSteer2 subset + carried-over 50 + Dolly) and the
   config file. Commit items before any model runs.
3. Write one harness, `v3_harness.py`, driven by the config, with resumable
   per-checkpoint saves and both readouts. Smoke it (phase 0).
4. Launch phase 1 on this box in the background. While it runs, write the v3
   analyzer against the smoke output so the analysis code predates the data.
5. Phase 2 on Kaggle (user runs, script is prepared here). Phase 4 API.
6. Fill H1 to H3 outcomes. Compare v2 vs v3 on the shared 50 items as a
   replication table.
7. Mechanism phase. Then write.

## 9. Things this plan does not fix

- Still no human judges as a comparison point. A small human study (3 raters,
  100 items, same perturbations) would show whether the tuning effect is an
  LLM property or a rater property. Worth doing if a reviewer asks; not
  budgeted here.
- Greedy/deterministic scoring remains. That is a feature of the readout, not a
  bug, but the sampled-readout comparison (P16) should be rerun at k = 32 on
  the frontier judges where sampling is cheap.
- Base checkpoints cannot be scored in chat format. The chat vs raw comparison
  is instruct-only by construction.
