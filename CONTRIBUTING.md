# Contributing to SAXIL Core

**Status:** Active for the official public repository `SayaOpenTech/saxil-core`.

## Scope

Contributions are accepted only to the **public SAXIL Core** surface (W2 codec, CLI, approved docs/spec/conformance). Research trees, models, gold corpora, STT/LLM/TTS stacks are out of scope.

## License + DCO

By contributing, you agree that your contribution is provided under the **Apache License, Version 2.0**. Contributors **retain** copyright in their contributions; contributing does not assign contributor rights beyond the Apache-2.0 grant.

Every commit must include a Developer Certificate of Origin sign-off. Use `git commit -s` to add a `Signed-off-by` trailer:

```
Signed-off-by: Full Name <email@example.com>
```

See [DCO.txt](DCO.txt) in this repository.

## Start with a reproducible public issue

Use the bug, usage-question or proposal forms in the
[issue tracker](https://github.com/SayaOpenTech/saxil-core/issues). Include the
SDK version/install source and a small synthetic reproduction. The current
public release is `saxil-core==0.1.0`; a source checkout may differ from it.

Keep PRs focused on a concrete problem and describe the validation you actually
performed. Use `python -m pytest tests -q` for source changes; examples should also
run against the released wheel as described in [examples/README.md](examples/README.md).
No model weights or research dependencies are needed for public examples.

See [feedback and adoption evidence](docs/ADOPTION_METRICS.md) for channels,
triage expectations, aggregate indicators and privacy limits.

## Merge authority

Only officially designated maintainers may merge to the official repository. Forks are free under Apache-2.0; they must not claim to be the official SAXIL product without separate permission.

## Brand / trademarks

Apache-2.0 does not grant Saya/SAXIL trademark rights. Descriptive references are fine; official-product or endorsement claims require separate permission.

## Code of conduct / security

For suspected vulnerabilities, follow [SECURITY.md](SECURITY.md). Do not disclose
vulnerability details in public issues or pull requests. Security reporting and
community support are best-effort, with no response or remediation SLA.
