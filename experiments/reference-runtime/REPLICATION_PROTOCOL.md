# Reference runtime: replication and release protocol

> Status update after execution (2026-10-29): all four frozen-checkpoint
> inference cohorts completed. See [actual revalidation](NATIVE_REVALIDATION.fa.md)
> and [run records](native_replay_status.json). The protocol and thresholds below
> are retained; completion does not turn historical yellow qualification green.

Protocol revision: 1; prepared 2026-10-29 before any new model run.
Status at preparation: local runtime candidate validated; historical model replay pending.

## Claims under evaluation

1. Historical exact-value selection/resolution outperforms direct numeric
   generation on the original zero-overlap D1 distribution.
2. Historical entity sidecar improves reference correctness over literal mode
   under the original SV3R distribution.
3. A reusable runtime preserves exact data and rejects invalid or stale
   references. This is an implementation claim independent of model quality.
4. Any advantage over JSON with the SAME references, resolver, semantic content,
   expected-role checks and failure behavior remains unestablished.

## A. Historical replay, without retraining first

- Freeze original scripts, corpus, token mapping, adapter weights, supplemental
  embeddings, base model revision/shards and environment with SHA256 checksums.
  Current hashes cannot by themselves prove identity with historical artifacts.
- Use read-only original checkpoints. All generated output goes to a new run
  directory. Never reuse the historical orchestrator unmodified: it creates
  corpora and trains in fixed original output directories.
- D1: evaluate both A and B final checkpoints on exactly the original 450 DEV
  IDs, greedy single pass, original max_new_tokens=48 and representation.
- SV3R: evaluate literal Arm A and sidecar Arm B on the same original 208 TEST
  IDs. Keep the original arm-specific interface and checkpoint selection.
- Original source inspection confirms that entity Arm A loads frozen SV3,
  whereas Arm B loads continued-trained SV3R. Reproduce that distinction; this
  historical comparison is not a same-checkpoint sidecar toggle. A causal
  representation comparison also needs matched adaptation/training opportunity.
- Emit per-row raw generated IDs, decoded predictions, references, resolver
  outcome and gold comparison. Independently recompute metrics from these rows.
- Compare paired predictions and aggregate scores to the archived CSVs. Report
  discrepancies and environment differences; do not tune on these original sets
  until they match. A failed replication is publishable as a negative result,
  not grounds to silently replace the historical claim.
- This replay is blocked until an appropriate governed launcher is available.
  Existing RSF/cpua launchers are different experiments and cannot substitute.

## B. Corrected new benchmark

- Keep original data immutable, including the 83 TRAIN and 15 DEV start_duration
  rows with target references missing from semantic input.
- Build a separately versioned corpus. Every target reference must point to
  data demonstrably present in the current input, explicit session state or
  a recorded tool result. Construct tables BEFORE constructing gold outputs.
  Never add records by scanning gold target output with bind_new=True.
- Fresh synthetic holdout seed: 20261029. Freeze its data and SHA256 before
  inference. Separate numeric/name pools and template families across splits;
  audit typed value overlap, exact literal overlap and role-template overlap.
- Include phones with leading zeros; unfamiliar names; two prices; min/max;
  start plus duration; two durations with distinct roles; same-type same-role
  distractors; unknown references; expired references; reset/reuse; type/unit
  mismatches; multi-entity selection; and empty tables.
- Preserve exact values as text, with domain validation separate. Do not claim
  arbitrary decimal/date support from a spelling-preservation test.

## C. Fair controls

- Direct generation; SAXIL reference path; JSON with equivalent references and
  resolver. Equal semantic information and external results for all arms.
- Distinguish native-token training from ordinary text/API prompting. A
  SAXIL-adapted model evaluated against untrained JSON is not a format-only
  comparison. Match base checkpoints, adaptation opportunity, training examples,
  epochs and decode settings; report token counts and compute actually used.
- If using a shared normalized model selection and two serializers, the test
  measures transport/runtime behavior only and cannot establish learned
  representation superiority.
- After the frozen-checkpoint replay, any newly trained comparison should use
  seeds 42, 43 and 44. Run only through authorized bounded experiment plans;
  record incomplete runs, unavailable GPU and timeouts as such.

## D. Metrics and gates fixed before new inference

- Primary model metric: exact final value/entity for the intended semantic role;
  invalid parses and rejected outputs count as incorrect. Report denominator,
  raw counts, per-family results, uncertainty and paired arm differences.
- Separate structural validity, correct action, reference identity, role binding,
  exact resolved bytes/text, and complete task success. Set equality of entity
  IDs alone is insufficient for role correctness.
- Preserve historical gates: the old VALUE_REF diagnostic required >=0.99 on
  isolated values, and historical SV3R had its own quality thresholds. Do not
  relabel the old yellow results green using weaker new thresholds.
- New model-backed release gate: >=0.99 exact final value/entity overall, >=0.95
  in every predeclared positive family, all designated malformed/stale/wrong-type
  references rejected without substitution. A same-role valid distractor may
  remain semantically wrong even if the runtime accepts it; count it as wrong.
- Runtime gate: every safety regression passes from an installed wheel, zero
  runtime dependencies, and no old reference revived after slot reuse/reset.
- An efficiency claim requires correctness within one percentage point of the
  control, paired measurements with uncertainty excluding no improvement, and
  recorded prompt/wrapper lengths, model tokens, timing scope, hardware and
  warmup. Report codec time, model time and end-to-end time separately.
- If JSON equivalence holds, say so. A ready implementation can still be useful;
  developer-time savings require a separate user study and are not inferred
  from lines of code or these automated checks.

## E. Publication gates

- Confirm redistributability and source provenance for each included asset.
  Entity training includes gold/VoiceAgent sources; names alone do not establish
  consent, anonymization or a redistribution license.
- Do not publish base weights, adapters, tokenizers or corpora by default.
  Publish only verified assets; provide reconstruction instructions for others.
- Record current artifact checksums, exact environment, approved launcher plan
  hash, per-run output manifest, raw non-sensitive results and negative cases.
- Keep original historical outputs distinct from corrected/new results and
  from the candidate runtime's deterministic unit tests.
- Decide final package/API and release license after audit. The current
  saxil-reference-runtime 0.0.0.dev0 name/version is local and provisional.
- Public Core W2 stays frozen unless a separately demonstrated wire requirement
  justifies a change. Neither VALUE_REF nor the sidecar inherently requires it.
