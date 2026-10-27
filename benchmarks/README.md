# Public reproducible serialization benchmark

This CPU-only benchmark compares W2 bytes with **compact UTF-8 JSON for the same
structured AST data**, and measures encode/decode operations. It uses the
published `saxil-core==0.1.0`, Python's standard library, and eight synthetic
records: six semantic frames and two closed-vocabulary verbal sequences.

## Data provenance and equivalence

[corpus.json](corpus.json) was authored for this public repository under
Apache-2.0. It contains no user conversations, private gold data, model outputs or
third-party dataset. The Persian strings are supported synthetic LEX units, not
an arbitrary-text compression test. Record IDs/provenance metadata are excluded
from both encoded representations.

Before timing, every original AST must equal both its W2-decoded and JSON-decoded
AST **across all dataclass fields**. Both representations must also roundtrip
canonically. A failure aborts measurement. This controls semantic equivalence for
these fixtures; it is not a claim that W2 preserves fields omitted by its profile
on arbitrary ASTs.

JSON uses sorted keys, no indentation or optional whitespace, UTF-8 and
`ensure_ascii=False`; type/field names are included so it can reconstruct the AST.
W2 sizes include its wire header. Neither gzip, HTTP framing nor natural-language
paraphrases enter the size comparison. JSON decoding includes constructing the
benchmark AST, and JSON encoding includes projecting it; these are named in the
results. Validation work still differs between formats.

## Reproduce

From a public checkout in a fresh virtual environment:

```sh
python -m pip install --only-binary=:all: saxil-core==0.1.0
python -I benchmarks/run_benchmark.py --iterations 1000 --trials 5 --output benchmark-results.json
```

The script requires an installed released wheel, warms up three corpus passes,
then records every trial using `perf_counter_ns`. It reports median operations
per second and ns/operation, source/script/corpus identifiers, and a small
environment description without hostname, user name, IP or local paths. The
corpus hash uses canonical UTF-8 JSON to avoid checkout line-ending differences.

CI uses a smaller CPU-only run for equivalence/execution checks and retains raw
JSON as an artifact. It has **no timing or compression-ratio pass threshold**.

## Limits and non-claims

- Eight deliberately chosen records are not a representative production corpus.
- W2's closed schema and vocabulary avoid JSON key/type overhead. A size result
  against this JSON schema cannot be generalized to all serialization formats.
- Results measure already structured messages, not lossless free-text Persian
  compression, universal LLM token/cost savings, or voice-agent speedup.
- Timings exclude network, STT/LLM/TTS, model adapters and application work; CPU
  load, Python version, hardware and differing validation affect them.
- This is a microbenchmark and a reproducible method, not an independent audit,
  performance SLA or statistically established superiority across workloads.

## Recorded sample

One Windows / CPython 3.13.14 run (1,000 iterations per record, five trials) gave:

| Quantity | Recorded value |
| --- | ---: |
| Structured records | 8 |
| Total W2 bytes | 124 |
| Total compact JSON UTF-8 bytes | 1,136 |
| W2 encode, median operations/s | 286,177 |
| W2 decode, median operations/s | 123,170 |
| JSON encode with AST projection, median operations/s | 63,203 |
| JSON decode with AST construction, median operations/s | 137,545 |

In this run, JSON-to-AST decoding was faster than W2 decoding. These numbers
describe this corpus, machine and operation definitions only; they are not a
general speed ranking. All individual trial durations are retained below.

The [checked-in sample](results/windows-python3.13.json) records one local run;
consult its raw trials and environment before interpreting it. Re-run on your own
machine and keep the raw output. See [SDK limitations](../docs/KNOWN_LIMITATIONS.md).
