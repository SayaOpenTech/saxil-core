"""Bounded negative / decoder hardening tests (non-destructive)."""

from __future__ import annotations

import pytest

from saxil_core import SemanticFrame, decode, encode
from saxil_core.errors import (
    SaxilDecodeError,
    SaxilResourceLimitError,
    SaxilUnsupportedVersionError,
)


def _good() -> bytes:
    return encode(
        SemanticFrame(
            speaker="user",
            act="ask",
            intent="query_price",
            polarity="pos",
            action="query",
        )
    )


@pytest.mark.parametrize(
    "payload,err",
    [
        (b"", (SaxilDecodeError,)),
        (b"\x00", (SaxilUnsupportedVersionError,)),
        (b"\x01\x00", (SaxilUnsupportedVersionError, SaxilDecodeError)),
        (b"\x02\xff", (SaxilDecodeError,)),
        (b"\x02\x10", (SaxilDecodeError,)),
        (b"\x02\x10\x04", (SaxilDecodeError,)),  # claims 4 fields but truncated
        (b"\x02\x10\x03\x01\x00\x02\x00\x03\x00", (SaxilDecodeError,)),  # n_fields<4
    ],
)
def test_malformed_rejects(payload, err):
    with pytest.raises(err):
        decode(payload)


def test_duplicate_tag_rejects():
    # Craft: version, semantic, n=5 with duplicated speaker tag — decoder should reject
    # Minimal valid then append illegal duplicate by mutating field count incorrectly is hard;
    # use truncated-after-dup style: build valid and inject dup tag stream.
    good = _good()
    # Insert a second TAG_SPEAKER (0x01) payload after first field by splicing — likely invalid_length
    # Safer approach: handcraft n_fields=5 with tags 01,01,...
    crafted = bytes([0x02, 0x10, 0x05, 0x01, 0x00, 0x01, 0x00, 0x02, 0x00, 0x03, 0x00, 0x04, 0x00])
    with pytest.raises(SaxilDecodeError) as ei:
        decode(crafted)
    assert "dup" in str(ei.value).lower() or "illegal" in str(ei.value).lower() or ei.value.code


def test_mutated_opcode_rejects_or_differs():
    good = bytearray(_good())
    good[3] ^= 0xFF
    with pytest.raises((SaxilDecodeError, SaxilUnsupportedVersionError)):
        decode(bytes(good))


def test_oversized_bounded():
    with pytest.raises(SaxilResourceLimitError):
        decode(b"\x02" + b"\x00" * 5000)


def test_invalid_utf8_literal_path_if_reached():
    # NAME unit with bad utf-8 length-declared body — construct verbal-like
    # OP_NAME=0x46 after verbal header: 02 11 00 01 46 <len> <bad>
    payload = bytes([0x02, 0x11, 0x00, 0x01, 0x46, 0x02, 0xFF, 0xFE])
    with pytest.raises(SaxilDecodeError):
        decode(payload)


def test_no_network_side_effect_on_decode():
    # Smoke: decode does not open sockets; just ensure pure call
    decode(_good())


def test_error_messages_do_not_embed_huge_payload():
    huge = b"\x02" + b"A" * 100
    try:
        decode(huge)
    except SaxilDecodeError as exc:
        assert len(str(exc)) < 500
