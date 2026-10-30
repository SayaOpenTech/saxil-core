# Experimental exact-reference runtime

This isolated research candidate preserves exact values and entity names outside
a model, then resolves model-selected references with type, role, unit and turn
checks. It is not part of the public `saxil-core==0.1.0` API. W2 and the SDK are
unchanged. There is no PyPI release or trained native-model bundle here.

See [the runtime API and limitations](candidate/README.md), the
[Persian evaluation report](FRESH_RESULTS.fa.md), and the
[historical replication protocol](REPLICATION_PROTOCOL.md).

## Fresh hosted-model evaluation

120 synthetic cases, 12 families, three inference seeds, three output formats;
1,080 requests to `qwen/qwen3.5-9b`, pinned to Parasail through OpenRouter.

| Output | Correct / all requests | Correct / returned responses | HTTP 429 |
|---|---:|---:|---:|
| Direct exact text in JSON | 355 / 360 | 355 / 355 | 5 |
| References in JSON | 359 / 360 | 359 / 359 | 1 |
| Short aliases with the same resolver | 358 / 360 | 358 / 358 | 2 |

No semantic or exact-copy error was observed in returned responses. The observed
overall accuracy differences came entirely from transport failures. This does
not establish an accuracy advantage for references or SAXIL over JSON.

Short aliases used about 83% fewer output tokens, and about 13.5% fewer total
tokens per successful response, than this JSON reference format. That is a
descriptive result for a short output notation in these cases. It does not
establish a unique SAXIL property, native-tokenizer efficiency, or universal
compression. JSON can use compact schemas too. Concurrent API wall times are
not native inference time or end-to-end voice latency.

The host already knows the requested semantic fields. A deterministic realizer
is also sufficient for these cases. Three inference seeds repeat the same 120
cases; they are not independent training replications.

## Offline reproduction

The compressed archive contains synthetic cases, frozen prompts/protocol/seals,
raw returned content and usage, HTTP failure records, and analysis. No historical
private corpora, checkpoint weights, credentials or audio are included.
The first provider failed preflight before any test cases; that attempt is
preserved separately. Both attempts used the same synthetic cases.

Check `study-artifacts.sha256`, then extract the archive in this directory:

```text
python -m tarfile -e study-artifacts.tar.gz .
python rescore_fresh_benchmark.py
python -m pip install ./candidate
python -m unittest discover -s candidate/tests -v
```

Independent rescoring checks all 1,080 raw outcomes and the frozen code/data
hashes. It matched the online scores exactly. No API key or network is needed
for rescoring or runtime tests. The runtime has zero required dependencies.

The `fresh_reference_benchmark_v2.py` runner is included for inspection and a
separately planned future run. It reads `OPENROUTER_API_KEY` from the environment,
has a fixed budget, and refuses to overwrite existing predictions. Do not remove
the archived results to rerun in place; use a separately versioned study.

## Frozen-checkpoint revalidation

All four original inference cohorts have now completed: VALUE arms A/B each
450 DEV cases, and ENTITY arms A/B each 208 TEST cases. Raw generated IDs were
decoded again and per-case scores checked against the evaluator. See the
[Persian revalidation report](NATIVE_REVALIDATION.fa.md),
[sanitized run evidence](native_replay_status.json), and
[archival comparison](native_archival_comparison.json).

The numeric experiment reproduced 52/450 exact values with direct generation
and 435/450 with VALUE_REF; every archived decoded value and primary score
matched in both arms. This supports reference selection for exact values in
this adapted-model diagnostic. Equivalent references and a resolver can be
implemented in JSON; this is not evidence of unique SAXIL superiority.

Entity A uses frozen SV3 and B uses continued-trained SV3R. Their comparison
includes a training difference. Legacy entity-set agreement also permits
empty-reference matches on invalid messages; the report includes parse and
joint task/field scores. Replaying existing weights is not independent retraining.

## Release status

The reference runtime and research evidence are experimental. The original
model-backed release gate (>=99% overall and >=95% per positive family) has not
been met; historical yellow qualification is retained. No trained model bundle
or PyPI/stable release is proposed here. Public W2 and SDK version 0.1.0 remain
unchanged. The independent runtime is not a native-tokenizer/model loader.

This candidate rejects stale, undefined, wrong-role and wrong-type references,
but it cannot recognize the wrong valid source among two records with the same
type/role/unit. Domain validation, model quality and deployment reliability
remain application responsibilities.

Both local base-weight shards match the official Qwen3.5-4B LFS digests; see
[base provenance](model_provenance.json). Adapter/corpus provenance remains a
separate gate for a future model bundle. No private model weights or corpora
are included. See [native readiness and remaining gates](native_readiness.json).

## Original-host identity capture

`inspect_replay_assets.py` hashes the original model, per-arm adapters,
supplemental embeddings, token mappings, tokenizer files, source helpers and
frozen evaluation sets without importing a model or initializing CUDA. It writes
only a new JSON file under the dedicated research artifact root and refuses to
overwrite it. Six CPU fixture tests cover its scope and missing-asset behavior.

All 42 inventoried files were hashed before replay and again afterward; their
contents are unchanged. Current hashes do not prove identity at the time of the
historical runs without historical reference digests. The native replay requires
the original research workspace and assets; the public archive reproduces the
separate synthetic hosted study, not those private model/data assets.
