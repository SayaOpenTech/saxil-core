# saxil-core (0.1.0) — SAXIL Core

Public SAXIL **W2** codec SDK under the **Apache License, Version 2.0**.

**SAXIL** = **Semantic Agent eXchange Intermediate Language**

**Human label:** `SAXIL Core 0.1.0`  
**Distribution status:** `PUBLIC`  
**License:** Apache-2.0 (see `LICENSE`)  
**Copyright:** 2026 Pedram Niloofari

Created by Pedram Niloofari. Part of the Saya AI ecosystem.  
Digital Bam is a commercial brand-use licensee candidate only where separately licensed; Digital Bam is **not** the creator of SAXIL.  
Apache-2.0 does **not** grant trademark rights in Saya/SAXIL names or logos.

## What is SAXIL Core?

A stdlib-only Python library that encodes and decodes **SAXIL W2** semantic and verbal messages (`byte0 == 2`) using a frozen AST and closed vocabulary tables.

## What does W2 encode?

Structured dialogue frames (`SemanticFrame`) and verbal unit sequences (`VerbalUtt`) — **not** arbitrary free-text Persian, and **not** a universal LLM tokenizer.

## Guarantees (W2-v1)

- Canonical encode/decode for supported AST values
- Fail-closed rejection of unsupported versions, unknown msg types, and malformed packets
- Deterministic wire bytes for the same AST under `W2-v1`

## Unsupported / out of scope

| Topic | Status |
|---|---|
| Free-text Persian auto-reversible compression | **No** — not lossless text ↔ W2 |
| S0.1 / V0.1 semantic readable forms | Deferred (not stable Core API) |
| `SAXIL_NATIVE_R2` | Frozen research; **not** exposed |
| Universal LLM token savings | **Not claimed** |
| Voice Agent E2E acceleration | **Not claimed** |
| AST `modality` / `uncertainty` on wire | Documented limitation (not emitted) |

## Install

```powershell
python -m pip install saxil-core==0.1.0
```

Offline / from a local wheel:

```powershell
python -m pip install --no-index --find-links=<path-to-dist> saxil-core==0.1.0
```

## Quick start

```python
from saxil_core import SemanticFrame, encode, decode, validate, get_version_info

frame = SemanticFrame(
    speaker="user",
    act="ask",
    intent="query_price",
    polarity="pos",
    action="query",
)
payload = encode(frame)          # bytes, wire version byte == 2
again = decode(payload)          # SemanticFrame
assert encode(again) == payload  # canonical round-trip
print(validate(payload))
print(get_version_info())
```

## CLI

```powershell
saxil --help
saxil version
saxil encode --hex -i frame.json
saxil decode --hex -i payload.hex --pretty
saxil validate --hex -i payload.hex
```

## Profiles

| Profile | In Core 0.1.0? |
|---|---|
| `W2-v1` | **Yes** (default) |
| `S0.1` / `V0.1` | Deferred (`saxil_core.sv` raises) |
| `SAXIL_NATIVE_R2` | Deferred (frozen; not modified) |

Unsupported profile names raise `SaxilUnsupportedProfileError`.

## Docs

See `docs/` in this package directory. W2 normative specification: `W2-v1-spec-1.0` (owner-approved).

## Tested vs declared

| Claim | Status |
|---|---|
| Declared `requires-python` | `>=3.10` |
| Classifiers | 3.10–3.13 |
| **Tested** Windows 11 + Python 3.13 | Yes (private RC + public isolation) |
| **Tested** WSL Ubuntu + Python 3.12 | Yes (private RC SDK suite) |
| Linux / macOS beyond above | **NOT_VERIFIED** as support SLA |

## Contributing

See `CONTRIBUTING.md` (DCO required). Contributors retain copyright.
