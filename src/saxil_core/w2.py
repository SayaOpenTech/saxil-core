"""Public W2 encode/decode/validate API.

Thin wrappers over the frozen vendored protocol.voice_extension.codec.
Wire format and AST contracts are unchanged.
"""

from __future__ import annotations

from typing import Any, Literal

from protocol.voice_extension.ast import Cmp, Date, Ent, Num, SemanticFrame, Time, VerbalUtt, VUnit
from protocol.voice_extension.codec import (
    MAX_PACKET,
    MSG_SEMANTIC,
    MSG_VERBAL,
    W2_VERSION,
    canonical_bytes as _canonical_bytes,
    decode_any as _decode_any,
    decode_semantic as _decode_semantic,
    decode_verbal as _decode_verbal,
    decode_w2 as _decode_w2,
    encode_semantic as _encode_semantic,
    encode_verbal as _encode_verbal,
    encode_w2 as _encode_w2,
)

from saxil_core._version import CODEC_PROFILE, SUPPORTED_PROFILES
from saxil_core.errors import (
    SaxilInvalidInputError,
    SaxilUnsupportedProfileError,
    SaxilValidationError,
    map_protocol_error,
    raise_mapped,
)

ProfileName = Literal["W2-v1"]


def _require_profile(profile: str | None) -> None:
    if profile is None:
        return
    if profile not in SUPPORTED_PROFILES:
        raise SaxilUnsupportedProfileError(
            "unsupported_profile",
            f"{profile!r} not in {SUPPORTED_PROFILES}; Core ships W2 only "
            "(S0.1/V0.1/NATIVE_R2 are deferred — see documentation)",
        )


def encode(
    obj: SemanticFrame | VerbalUtt,
    *,
    profile: str = CODEC_PROFILE,
) -> bytes:
    """Encode a W2 AST object to wire bytes (canonical encoder)."""
    _require_profile(profile)
    if not isinstance(obj, (SemanticFrame, VerbalUtt)):
        raise SaxilInvalidInputError(
            "invalid_input",
            f"expected SemanticFrame or VerbalUtt, got {type(obj).__name__}",
        )
    try:
        return _encode_w2(obj)
    except Exception as exc:  # noqa: BLE001 — map protocol failures
        raise_mapped(exc)
        raise  # pragma: no cover


def decode(
    payload: bytes | bytearray | memoryview,
    *,
    profile: str = CODEC_PROFILE,
) -> SemanticFrame | VerbalUtt:
    """Decode W2 bytes to AST. Rejects W1 (use decode_any for W1+W2)."""
    _require_profile(profile)
    buf = _as_bytes(payload)
    try:
        return _decode_w2(buf)
    except Exception as exc:  # noqa: BLE001
        raise_mapped(exc)
        raise  # pragma: no cover


def decode_any(
    payload: bytes | bytearray | memoryview,
    *,
    profile: str | None = None,
) -> Any:
    """Decode W1 (byte0==1) or W2 (byte0==2). Profile must be W2-v1 or omitted."""
    if profile is not None:
        _require_profile(profile)
    buf = _as_bytes(payload)
    try:
        return _decode_any(buf)
    except Exception as exc:  # noqa: BLE001
        raise_mapped(exc)
        raise  # pragma: no cover


def validate(
    payload: bytes | bytearray | memoryview,
    *,
    profile: str = CODEC_PROFILE,
) -> dict[str, Any]:
    """Validate a W2 payload by decoding and re-encoding (canonical check).

    Returns a machine-readable report. Does not silently repair bytes.
    """
    _require_profile(profile)
    buf = _as_bytes(payload)
    try:
        obj = _decode_w2(buf)
        canon = _encode_w2(obj)
    except Exception as exc:  # noqa: BLE001
        mapped = map_protocol_error(exc)
        raise SaxilValidationError(mapped.code, mapped.message, cause=exc) from exc
    return {
        "ok": True,
        "profile": profile,
        "wire_version": buf[0] if buf else None,
        "msg_type": buf[1] if len(buf) > 1 else None,
        "payload_bytes": len(buf),
        "canonical_bytes": len(canon),
        "is_canonical_encoding": buf == canon,
        "ast_type": type(obj).__name__,
    }


def encode_w2(obj: SemanticFrame | VerbalUtt) -> bytes:
    return encode(obj)


def decode_w2(payload: bytes | bytearray | memoryview) -> SemanticFrame | VerbalUtt:
    return decode(payload)


def encode_semantic(frame: SemanticFrame) -> bytes:
    if not isinstance(frame, SemanticFrame):
        raise SaxilInvalidInputError("invalid_input", "expected SemanticFrame")
    try:
        return _encode_semantic(frame)
    except Exception as exc:  # noqa: BLE001
        raise_mapped(exc)
        raise  # pragma: no cover


def decode_semantic(payload: bytes | bytearray | memoryview) -> SemanticFrame:
    try:
        return _decode_semantic(_as_bytes(payload))
    except Exception as exc:  # noqa: BLE001
        raise_mapped(exc)
        raise  # pragma: no cover


def encode_verbal(utt: VerbalUtt) -> bytes:
    if not isinstance(utt, VerbalUtt):
        raise SaxilInvalidInputError("invalid_input", "expected VerbalUtt")
    try:
        return _encode_verbal(utt)
    except Exception as exc:  # noqa: BLE001
        raise_mapped(exc)
        raise  # pragma: no cover


def decode_verbal(payload: bytes | bytearray | memoryview) -> VerbalUtt:
    try:
        return _decode_verbal(_as_bytes(payload))
    except Exception as exc:  # noqa: BLE001
        raise_mapped(exc)
        raise  # pragma: no cover


def canonical_bytes(obj: SemanticFrame | VerbalUtt) -> bytes:
    try:
        return _canonical_bytes(obj)
    except Exception as exc:  # noqa: BLE001
        raise_mapped(exc)
        raise  # pragma: no cover


def _as_bytes(payload: bytes | bytearray | memoryview) -> bytes:
    if payload is None:  # type: ignore[comparison-overlap]
        raise SaxilInvalidInputError("invalid_input", "payload is None")
    if isinstance(payload, memoryview):
        payload = payload.tobytes()
    if isinstance(payload, bytearray):
        payload = bytes(payload)
    if not isinstance(payload, (bytes, bytearray)):
        raise SaxilInvalidInputError(
            "invalid_input",
            f"payload must be bytes-like, got {type(payload).__name__}",
        )
    if len(payload) > MAX_PACKET:
        # Match codec fail-closed before decode where possible
        from saxil_core.errors import SaxilResourceLimitError

        raise SaxilResourceLimitError("oversized", f"packet length {len(payload)} > {MAX_PACKET}")
    return bytes(payload)


__all__ = [
    "W2_VERSION",
    "MSG_SEMANTIC",
    "MSG_VERBAL",
    "SemanticFrame",
    "VerbalUtt",
    "VUnit",
    "Ent",
    "Num",
    "Date",
    "Time",
    "Cmp",
    "encode",
    "decode",
    "validate",
    "encode_w2",
    "decode_w2",
    "decode_any",
    "encode_semantic",
    "decode_semantic",
    "encode_verbal",
    "decode_verbal",
    "canonical_bytes",
]
