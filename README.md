# SAXIL Core

**Encode structured semantic and verbal messages as deterministic W2 binary
packets, then decode and validate them in Python.**

[![Public CI](https://github.com/SayaOpenTech/saxil-core/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SayaOpenTech/saxil-core/actions/workflows/ci.yml)

SAXIL means **Semantic Agent eXchange Intermediate Language**. The public
`saxil-core` package is a Python SDK and CLI with no mandatory third-party runtime
dependencies. The published version is **0.1.0**, using the frozen **W2-v1** profile.

## When to use it

Use SAXIL Core when your application already has structured dialogue data and
needs a shared, deterministic wire representation:

- Exchange supported intent/action/entity frames between services or agent components.
- Encode supported verbal unit sequences using `VerbalUtt`.
- Decode and validate W2 packets at an application boundary.
- Check canonical byte roundtrips and inspect packets through the CLI.

Your application supplies the structured data. SAXIL Core does not extract intent
from free text, run a language model, or provide a network transport.

## Install the released SDK

Requires **Python 3.10 or later**. In a virtual environment:

```sh
python -m pip install saxil-core==0.1.0
python -m saxil_core version
```

See the [installation guide](docs/INSTALLATION.md) for environment setup and
offline installation. Installation can require network access; W2 encoding and
decoding run locally without a model or online service.

## Try a canonical roundtrip

```python
from saxil_core import SemanticFrame, decode, encode, validate

frame = SemanticFrame(
    speaker="user",
    act="ask",
    intent="query_price",
    polarity="pos",
    action="query",
)

payload = encode(frame)          # bytes in the W2-v1 profile
restored = decode(payload)       # SemanticFrame
assert encode(restored) == payload

print(payload.hex())
print(validate(payload))
```

The assertion checks canonical wire bytes. Supported values come from a closed
vocabulary; arbitrary strings are not automatically valid AST values. See the
[AST contract](docs/W2_AST_CONTRACT.md) and [encoder/decoder behavior](docs/ENCODER_DECODER_BEHAVIOR.md).

## Use the CLI

Save this as `frame.json` in UTF-8:

```json
{
  "type": "semantic",
  "speaker": "user",
  "act": "ask",
  "intent": "query_price",
  "polarity": "pos",
  "action": "query"
}
```

Then run:

```sh
python -m saxil_core encode --hex -i frame.json -o frame.hex
python -m saxil_core decode --hex -i frame.hex --pretty
python -m saxil_core validate --hex -i frame.hex
```

The installed `saxil` command exposes the same interface.
Use `python -m saxil_core --help` for command help. Handle SDK errors and CLI exit
codes as described in [error handling](docs/ERROR_HANDLING.md).

## Boundaries and limitations

- W2 represents supported `SemanticFrame` and `VerbalUtt` data. It is not a
  lossless compressor for arbitrary Persian text or a general replacement for an
  LLM tokenizer.
- No universal token/cost savings or end-to-end voice-agent speedup is claimed.
- W2-v1 has a frozen AST/vocabulary contract. In particular, AST `modality` and
  `uncertainty` fields are not emitted on the wire; a canonical byte roundtrip
  does not promise preservation of every Python AST field.
- `S0.1`, `V0.1`, and `SAXIL_NATIVE_R2` are not supported public Core profiles.
  Unsupported profile names raise `SaxilUnsupportedProfileError`.
- Malformed packets, unsupported versions and invalid values are rejected;
  applications still need to handle errors and their own input/trust boundaries.
- [Public CI](https://github.com/SayaOpenTech/saxil-core/actions/workflows/ci.yml)
  exercises the public SDK on Linux and Windows with Python 3.10–3.13. The
  declared minimum Python version is not a claim that every newer version or
  other operating system has been verified, and there is no support SLA.

See [known limitations](docs/KNOWN_LIMITATIONS.md) for more detail. Model weights,
research adapters and training/inference stacks are not included in the SDK.

## Documentation

Browse the [documentation website](https://sayaopentech.github.io/saxil-core/) or
use the source pages below.

| Start here | Reference |
| --- | --- |
| [Installation](docs/INSTALLATION.md) | [Python API](docs/API_REFERENCE.md) |
| [Quick start](docs/QUICKSTART.md) | [AST contract](docs/W2_AST_CONTRACT.md) |
| [Three executable examples](examples/README.md) | [Encoder/decoder behavior](docs/ENCODER_DECODER_BEHAVIOR.md) |
| [Python service integration](integrations/price_service/README.md) | [Public benchmarks](benchmarks/README.md) |
| [Feedback and adoption evidence](docs/ADOPTION_METRICS.md) | [Security reporting](SECURITY.md) |
| [Offline usage](docs/OFFLINE_USAGE_EXAMPLE.md) | [Version/profile compatibility](docs/VERSION_PROFILE_COMPATIBILITY.md) |
| [Error handling](docs/ERROR_HANDLING.md) | [Frozen W2-v1 specification](docs/W2-v1-spec-1.0.md) |

[Release 0.1.0](https://github.com/SayaOpenTech/saxil-core/releases/tag/v0.1.0)
and [PyPI 0.1.0](https://pypi.org/project/saxil-core/0.1.0/) contain the published
distributions. See the [changelog](CHANGELOG.md) for release information.

## Contribute or report a problem

For reproducible bugs or usage questions, use the
[public issue tracker](https://github.com/SayaOpenTech/saxil-core/issues).
For suspected vulnerabilities, follow [SECURITY.md](SECURITY.md) and use the
private reporting channel; keep vulnerability details out of public issues.

Contributions follow [CONTRIBUTING.md](CONTRIBUTING.md) and require a
[DCO sign-off](DCO.txt). Contributors retain copyright in their contributions.

## License and attribution

Created by **Pedram Niloofari**, part of the Saya AI ecosystem.
Copyright 2026 Pedram Niloofari. Code is licensed under [Apache-2.0](LICENSE);
see [NOTICE](NOTICE). Trademark rights in Saya/SAXIL names and logos are separate
and are not granted by the code license.
