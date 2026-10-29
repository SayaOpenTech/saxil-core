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

## Release status

Historical 4B checkpoint inference has not been replayed. Runner startup has
now recovered in official probe RUN-20261029-0008, and the original Linux
environment is available. A dedicated governed replay launcher and its actual
execution are still pending. This hosted 9B study is not that replication.
See [current native readiness](native_readiness.json).

This candidate rejects stale, undefined, wrong-role and wrong-type references,
but it cannot recognize the wrong valid source among two records with the same
type/role/unit. Domain validation, model quality, and deployment reliability
remain application responsibilities. The code and synthetic study are a draft
for research review, not a production-readiness claim.

## Preparing original-host identity capture

`inspect_replay_assets.py` can hash the original model, per-arm adapters,
supplemental embeddings, token mappings, tokenizer files, source helpers and
frozen evaluation sets without importing a model or initializing CUDA. It writes
only a new JSON file under the dedicated research artifact root and refuses to
overwrite it. Six CPU fixture tests cover its scope and missing-asset behavior.
It has now hashed all 42 expected original files and verified evaluation-set
counts (450 values, 208 entity cases); this does not authorize an experiment.

Original entity Arm A used frozen SV3; Arm B used continued-trained SV3R.
Replaying the same checkpoint in both arms would not reproduce that experiment.
Current artifact hashes also cannot establish historical identity without an
original reference digest. Registration/execution on the original Runner host
remains a separate governed step.
