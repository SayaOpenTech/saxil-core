# Python quote-service integration

This first-party, CPU-only integration demonstrates a concrete Python application
using the **published** `saxil-core==0.1.0`. A client sends a structured price
query as W2 bytes; a separate service looks up a fictitious catalog and returns a
typed price statement as W2. No LLM, research adapter, API key or network service
outside loopback is required after installing the wheel.

## Run the complete demo

From the public repository root in a fresh virtual environment:

```sh
python -m pip install --only-binary=:all: saxil-core==0.1.0
python -I integrations/price_service/run_demo.py
```

The runner verifies the installed SDK/version, starts the service on a free
loopback port, runs the client in another Python process, checks product 1's
synthetic quote (`42000`, `toman`), and exercises five rejection paths. It cleans
up the process on success or failure. CI repeats this on Linux/Windows with
Python 3.10/3.13 using the released wheel, not a checkout installation.

To inspect the two application processes manually, in one terminal:

```sh
python -I integrations/price_service/service.py --port 8766
```

Then in another terminal with the same environment:

```sh
python -I integrations/price_service/client.py http://127.0.0.1:8766/quote --product-id 1
```

The service handles one request by default and exits. The client prints the
decoded product/price/unit and request/response byte lengths. The JSON printed
to the terminal is presentation output; successful HTTP request/response bodies
are binary W2.

## Application contract and interoperability

| Layer | Demo behavior |
| --- | --- |
| HTTP | `POST /quote`, `application/octet-stream`, explicit content length, loopback only |
| Request AST | `SemanticFrame`: user / ask / query_price / pos / query; product `Ent.eid` |
| Response AST | `SemanticFrame`: agent / assert / state_price / pos / state; same product ID; `attribute=Num(price, unit)` |
| Invalid W2 | HTTP 400 |
| Valid W2 with unsupported business intent/shape | HTTP 422 |
| Unknown synthetic product | HTTP 404 |
| Wrong media type | HTTP 415 |
| Empty or oversized body | HTTP 413 |

The SDK validates representation; the application separately checks which
decoded frames it will act on. Valid W2 does not automatically authorize an
operation or make every intent meaningful to this service. Only successful
responses use W2; HTTP error responses use status codes and the standard-library
HTTP error body. Transport framing, catalog IDs, units and business decisions
are application conventions, not a new SAXIL protocol/profile or SDK API.

## Boundaries

`catalog.json` is synthetic Apache-2.0 demonstration data, not real prices or
customer data. The service binds only to `127.0.0.1`, uses finite request counts,
timeouts and a small body limit. Authentication, TLS, persistence, concurrency,
retries and external deployment are outside this finite local demonstration.
The client accepts product IDs in `1..255`, within the existing W2 entity-ID
representation. Only IDs 1 and 2 are present in this synthetic catalog.

This shows structured interoperability with a Python service. It does not teach
an LLM to understand W2, convert arbitrary Persian text, or establish token/cost
savings or end-to-end voice performance. It is **first-party evidence**, not an
independent external adoption claim. Compare the earlier
[three examples](../../examples/README.md) and [adoption definitions](../../docs/ADOPTION_METRICS.md).
