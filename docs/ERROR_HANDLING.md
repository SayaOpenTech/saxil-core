# Error Handling

| SDK error | Typical cause |
|---|---|
| `SaxilInvalidInputError` | Wrong Python type for encode/decode |
| `SaxilDecodeError` | Truncated / corrupt / invalid opcodes |
| `SaxilUnsupportedVersionError` | `byte0` not accepted for operation |
| `SaxilUnsupportedProfileError` | Profile ≠ `W2-v1` (or S/V deferred) |
| `SaxilValidationError` | `validate()` failed |
| `SaxilResourceLimitError` | Oversized packet / limits |

Underlying `W2Error` / `VersionError` / `DecodeError` are mapped; original exception is available as `__cause__`.

CLI writes errors to **stderr** and exits with code `1` (usage errors: argparse `2`).
