# API Reference (saxil_core)

## Version

- `SOFTWARE_VERSION` / `__version__` → `0.1.0-rc.1`
- `get_version_info() -> dict`
- `CODEC_PROFILE` → `"W2-v1"`
- `PROTOCOL_W2_VERSION` → `2`

## Encode / decode / validate

| Function | Description |
|---|---|
| `encode(obj, *, profile="W2-v1") -> bytes` | Canonical W2 encode |
| `decode(payload, *, profile="W2-v1")` | W2-only decode |
| `decode_any(payload)` | W1 or W2 |
| `validate(payload, *, profile="W2-v1") -> dict` | Decode + re-encode report |
| `encode_semantic` / `decode_semantic` | Semantic-only |
| `encode_verbal` / `decode_verbal` | Verbal-only |
| `canonical_bytes(obj)` | Alias of canonical encode |

## AST types

Re-exported from frozen W2 AST: `SemanticFrame`, `VerbalUtt`, `VUnit`, `Ent`, `Num`, `Date`, `Time`, `Cmp`.

## Errors

See `ERROR_HANDLING.md`.
