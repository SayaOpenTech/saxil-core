# Released W2 vs strong JSON: independently framed message study

This bounded engineering study uses the released `saxil-core==0.1.0` wheel.
It measures already structured supported ASTs, not NLU, LLM accuracy or free-text
compression. See [the Persian report](REPORT.fa.md) for scope and limitations.

Evidence: [full size/timing summary](results-v1/summary.json),
[independent recomputation](results-v1/independent_audit_v2.json),
[actual TCP receiver results](results-v1/transport-v1/summary.json), and
[runtime versions](EXPERIMENT_ENVIRONMENT.json).

4,608 synthetic cases cover 12 families and three fixed seeds. Both W2 and JSON
retain every dataclass field in every case. Against the best declared JSON
encoding/compression per message, W2 uses 27.50% fewer framed bytes on semantic
frames and 35.97% fewer on structured verbal messages. All-message reduction is
31.09%. JSON is smaller on one case and tied on four; none are excluded.

JSON has shared enum/LEX dictionaries, dense/sparse defaults, UTF-8 without
whitespace, and an optimistic best choice among three encodings and five
compression modes. Both sides pay the same framing/codec-marker overhead.
Batch compression reduces the advantage to about 3.5%. Other binary codecs and
all conceivable JSON schemas were not compared. Timing results describe these
implementations and differing validation work; they do not establish universal
codec or end-to-end speed superiority.

An actual separate-process loopback TCP check delivered all 4,608 messages per
arm with zero AST-digest/order discrepancies: 215,798 forward application bytes
for W2 and 313,173 for JSON, including a four-byte termination frame. Network
packet/TLS overhead is not measured. This is the same synthetic corpus, not an
independent deployment or external-user pilot.

## Reproduce

Use an isolated environment with the released wheel, not a development import:

```sh
python -m venv .venv
# Activate .venv using the command appropriate for your operating system.
python -m pip download --only-binary=:all: --no-deps saxil-core==0.1.0 -d wheels
# Expected SHA256: 28c56cb52849bd6f4803d3e322ee7b93f2a1c1a48a4532aa41fca655347d3cf0
python -m pip install --no-index --no-deps wheels/saxil_core-0.1.0-py3-none-any.whl
```

Verify `study-artifacts.sha256`, extract the archive into this directory, then:

```sh
python audit_results.py --verify-frozen
```

The portable audit checks all original raw packets, AST fields, per-case byte
counts, primary totals, archived hashes and batch summaries without requiring
another zlib version to reproduce the same compressed stream. The original
full audit also recomputes every compression minimum and batch size using the
recorded Python 3.13.14/zlib 1.3.1 environment:

```sh
python audit_results.py --out audit-new.json
python run_study.py --out results-reproduction
python transport_check.py --out transport-reproduction
```

All commands refuse to overwrite existing output. Reproduction timings and
compression choices may change with hardware/runtime; report them as a new run.
`build_corpus.py` is included for inspecting generation, and refuses to replace
the frozen corpus or seal. Copy sources into a separately versioned study if
changing generation or a sealed script. No API key, GPU or model is needed.

The protocol was recorded locally before measurement, not in an external
timestamped registration service. Initial invalid-domain generator assumptions
were corrected before any size/timing result and are retained transparently in
`PREFLIGHT_NOTES.md` and the original draft protocol. Synthetic data and study
code are released under the repository's Apache-2.0 license; no customer data,
private historical corpus, model weights or credentials are included.
