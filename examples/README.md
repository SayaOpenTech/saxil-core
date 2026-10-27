# Three executable W2 examples

These examples use only Python's standard library and the **published**
`saxil-core==0.1.0`. No model, research adapter, private data or API key is needed.
All example frames and packets are synthetic and provided under this repository's
Apache-2.0 license. They do not represent user conversations or external datasets.

In a fresh virtual environment, from the public repository root:

```sh
python -m pip install --only-binary=:all: saxil-core==0.1.0
python -I examples/run_examples.py
```

The runner verifies the installed version and import location, starts two
separate Python processes for the loopback exchange, and fails if an expected
roundtrip or rejection does not occur. CI repeats this on Linux and Windows with
Python 3.10 and 3.13. Loopback access is required for the second example.

## 1. Structured message roundtrip

```sh
python -I examples/roundtrip.py
```

Constructs a supported `SemanticFrame`, encodes it, decodes it, and checks
canonical wire bytes. It prints a 13-byte packet and `intent=query_price`.
Canonicalization does not imply preservation of AST fields absent from W2-v1.

## 2. Exchange between two Python services

The automated runner starts `service_exchange/receiver.py` and then
`service_exchange/sender.py`. To inspect the exchange manually, in one terminal:

```sh
python -I examples/service_exchange/receiver.py --port 8765
```

In a second terminal using the same environment:

```sh
python -I examples/service_exchange/sender.py http://127.0.0.1:8765/w2
```

The receiver handles one request, decodes and re-encodes its packet, returns W2
bytes, and exits. The sender checks that the response matches its canonical
request. HTTP method/path, content length and `application/octet-stream` are
application transport choices, not additions to the W2 specification.

The receiver binds to loopback, has a small body limit and timeouts, and provides
no authentication or remote deployment configuration. Its single-request echo
behavior demonstrates serialization across a process boundary, not a complete
production service, semantic task execution, delivery guarantee or AI inference.

## 3. Invalid and unsupported packet handling

```sh
python -I examples/invalid_packets.py
```

Shows public `SaxilCoreError` handling for an empty packet, truncation, unsupported
version and unknown message type. It prints the concrete error class/code and
fails if any of these packets is unexpectedly accepted. This is a small usage
example, not exhaustive fuzzing or proof that arbitrary input is safe.

See [error handling](../docs/ERROR_HANDLING.md), [known limitations](../docs/KNOWN_LIMITATIONS.md),
and the [frozen W2 specification](../docs/W2-v1-spec-1.0.md).
