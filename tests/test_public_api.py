"""Public SDK API tests (stdlib + package only)."""

from __future__ import annotations

import pytest

from saxil_core import (
    CODEC_PROFILE,
    SOFTWARE_VERSION,
    SemanticFrame,
    SaxilDecodeError,
    SaxilInvalidInputError,
    SaxilUnsupportedProfileError,
    SaxilUnsupportedVersionError,
    VerbalUtt,
    VUnit,
    canonical_bytes,
    decode,
    decode_any,
    encode,
    get_version_info,
    validate,
)


def _simple_frame() -> SemanticFrame:
    return SemanticFrame(
        speaker="user",
        act="ask",
        intent="query_price",
        polarity="pos",
        action="query",
    )


def test_version_info():
    info = get_version_info()
    assert info["software_version"] == SOFTWARE_VERSION
    assert info["codec_profile"] == "W2-v1"
    assert info["distribution_status"] == "PUBLIC"
    assert "W2-v1" in info["supported_profiles"]


def test_encode_decode_roundtrip_identity_bytes():
    frame = _simple_frame()
    b1 = encode(frame)
    obj = decode(b1)
    b2 = encode(obj)
    assert b1 == b2 == canonical_bytes(frame)
    assert isinstance(obj, SemanticFrame)
    assert obj.intent == "query_price"
    assert obj.polarity == "pos"


def test_deterministic_encoding():
    frame = _simple_frame()
    assert encode(frame) == encode(frame)


def test_verbal_roundtrip():
    utt = VerbalUtt("statement", (VUnit("LEX", w="قیمت"), VUnit("LEX", w="این")))
    b = encode(utt)
    out = decode(b)
    assert isinstance(out, VerbalUtt)
    assert encode(out) == b


def test_validate_ok():
    b = encode(_simple_frame())
    report = validate(b)
    assert report["ok"] is True
    assert report["is_canonical_encoding"] is True
    assert report["profile"] == CODEC_PROFILE


def test_unsupported_profile():
    with pytest.raises(SaxilUnsupportedProfileError):
        encode(_simple_frame(), profile="SAXIL_NATIVE_R2")
    with pytest.raises(SaxilUnsupportedProfileError):
        decode(b"\x02\x10", profile="S0.1")


def test_invalid_input_type():
    with pytest.raises(SaxilInvalidInputError):
        encode("not-an-ast")  # type: ignore[arg-type]
    with pytest.raises(SaxilInvalidInputError):
        decode("not-bytes")  # type: ignore[arg-type]


def test_empty_payload():
    with pytest.raises(SaxilDecodeError):
        decode(b"")


def test_unsupported_version_byte():
    with pytest.raises(SaxilUnsupportedVersionError):
        decode(b"\x00\x10")


def test_w1_rejected_by_decode_w2_path():
    # Minimal truncated W1-like header: version 1
    with pytest.raises(SaxilUnsupportedVersionError):
        decode(b"\x01\x01")


def test_decode_any_rejects_unknown_version():
    with pytest.raises(SaxilUnsupportedVersionError):
        decode_any(b"\x09\x00")


def test_truncated_and_corrupt():
    good = encode(_simple_frame())
    with pytest.raises(SaxilDecodeError):
        decode(good[:3])
    mutated = bytearray(good)
    if len(mutated) > 3:
        mutated[3] ^= 0xFF
        with pytest.raises((SaxilDecodeError, SaxilUnsupportedVersionError)):
            decode(bytes(mutated))


def test_oversized_rejected():
    from saxil_core.errors import SaxilResourceLimitError

    huge = b"\x02" + b"\x00" * 5000
    with pytest.raises(SaxilResourceLimitError):
        decode(huge)


def test_sv_module_deferred():
    from saxil_core import sv

    assert sv.available() is False
    with pytest.raises(SaxilUnsupportedProfileError):
        sv.encode()
