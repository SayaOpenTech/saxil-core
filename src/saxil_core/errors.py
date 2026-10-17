"""SDK-level errors. Wrap underlying protocol errors without changing wire behavior."""

from __future__ import annotations

from typing import Any


class SaxilCoreError(Exception):
    """Base error for saxil-core."""

    def __init__(self, code: str, message: str = "", *, cause: BaseException | None = None) -> None:
        self.code = code
        self.message = message
        self.cause = cause
        text = f"{code}: {message}" if message else code
        super().__init__(text)


class SaxilInvalidInputError(SaxilCoreError):
    """AST / argument type is not valid for the selected operation."""


class SaxilDecodeError(SaxilCoreError):
    """Malformed, truncated, or otherwise undecodable payload."""


class SaxilUnsupportedVersionError(SaxilCoreError):
    """Wire version byte is not supported for the requested operation."""


class SaxilUnsupportedProfileError(SaxilCoreError):
    """Requested codec profile is not part of this Core package."""


class SaxilValidationError(SaxilCoreError):
    """Payload failed validate() checks."""


class SaxilResourceLimitError(SaxilCoreError):
    """Packet / literal / nesting limits exceeded."""


def map_protocol_error(exc: BaseException) -> SaxilCoreError:
    """Map frozen protocol exceptions to SDK errors (fail-closed; no silent repair)."""
    # Import locally to keep errors module light if protocol missing during tooling.
    from protocol.reference.sml_runtime.errors import DecodeError, VersionError
    from protocol.voice_extension.codec import W2Error

    name = type(exc).__name__
    text = str(exc)

    if isinstance(exc, VersionError):
        return SaxilUnsupportedVersionError("unsupported_version", text, cause=exc)
    if isinstance(exc, W2Error):
        code = getattr(exc, "code", None) or "decode_failure"
        if code in ("oversized",):
            return SaxilResourceLimitError(code, text, cause=exc)
        if code in ("truncate", "unterminated_literal", "invalid_varint", "trailing_garbage"):
            return SaxilDecodeError(code, text, cause=exc)
        if code in ("invalid_opcode", "invalid_enum", "unknown_msg_type", "invalid_length"):
            return SaxilDecodeError(code, text, cause=exc)
        return SaxilDecodeError(code, text, cause=exc)
    if isinstance(exc, DecodeError):
        return SaxilDecodeError("decode_failure", text, cause=exc)
    return SaxilCoreError("decoder_failure", f"{name}: {text}", cause=exc)


def raise_mapped(exc: BaseException) -> None:
    mapped = map_protocol_error(exc)
    raise mapped from exc
