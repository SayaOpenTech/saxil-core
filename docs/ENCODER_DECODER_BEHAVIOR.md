# Encoder / Decoder Behavior

## Guarantees (W2 Core)

1. **Deterministic encode** for a given AST object.
2. **Lossless AST ↔ bytes** under the W2 contract (canonical round-trip on bytes).
3. **Fail-closed** on malformed / wrong version / oversized payloads.
4. **No silent repair** of invalid messages.

## Non-guarantees

1. `decode(encode(x))` returns an object equal by `==` for all nested fields — dataclasses are frozen and fields are reconstructed; equality holds for supported structures in practice, but the **contractual** guarantee emphasized by Core is **canonical byte identity** after re-encode.
2. Persian wording preservation (use S/V research path; lossy by design).
3. Compatibility with Native R2 token IDs (deferred package).

## Profile selection

Default profile `W2-v1`. Unsupported profiles raise `SaxilUnsupportedProfileError` before touching the codec.
The W2 wire already embeds version byte `2`; Core does not add an outer envelope.
