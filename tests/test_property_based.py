"""Bounded property-based tests for W2 Core (deterministic seed)."""

from __future__ import annotations

import random
from dataclasses import replace

import pytest

from protocol.voice_extension import dicts as D
from saxil_core import (
    Ent,
    SemanticFrame,
    VerbalUtt,
    VUnit,
    decode,
    encode,
)
from saxil_core.errors import SaxilCoreError, SaxilUnsupportedProfileError

SEED = 20261016
N_CASES = 200


def _rng():
    return random.Random(SEED)


def _gen_frame(r: random.Random) -> SemanticFrame:
    speaker = r.choice(D.SPEAKER)
    act = r.choice(D.ACT)
    intent = r.choice(D.INTENT)
    polarity = r.choice(D.POLARITY)
    action = r.choice([None, r.choice(D.ACTION)])
    obj = None
    if r.random() < 0.4:
        obj = Ent(
            eid=r.randint(1, 8),
            typ=r.choice([t for t in D.ENT_TYPE if t]),
            ref=r.choice([x for x in D.REF if x] + [None]),
            name=None,
        )
    qtype = r.choice([None] + [x for x in D.QTYPE if x])
    request = r.choice([None] + [x for x in D.REQUEST if x])
    affect = r.choice([None] + [x for x in D.AFFECT if x])
    return SemanticFrame(
        speaker=speaker,
        act=act,
        intent=intent,
        polarity=polarity,
        action=action,
        object=obj,
        qtype=qtype,
        request=request,
        affect=affect,
    )


def _gen_verbal(r: random.Random) -> VerbalUtt:
    utt = r.choice(D.UTT_TYPE)
    n = r.randint(1, 5)
    units = []
    for _ in range(n):
        w = r.choice(D.LEX[:40])
        units.append(VUnit("LEX", w=w))
    return VerbalUtt(utt_type=utt, units=tuple(units))


def test_p1_p2_p3_p4_semantic_properties():
    r = _rng()
    failures = []
    for i in range(N_CASES):
        fr = _gen_frame(r)
        try:
            b1 = encode(fr)
            b2 = encode(fr)
            assert b1 == b2  # P2
            obj = decode(b1)
            b3 = encode(obj)
            assert b3 == b1  # P3 / canonical stability
            decode(b3)  # P4
        except Exception as exc:  # noqa: BLE001
            failures.append((i, fr, type(exc).__name__, str(exc)))
            if len(failures) >= 3:
                break
    assert not failures, failures[:3]


def test_p1_p2_p3_verbal_properties():
    r = _rng()
    failures = []
    for i in range(N_CASES):
        utt = _gen_verbal(r)
        try:
            b1 = encode(utt)
            assert encode(utt) == b1
            assert encode(decode(b1)) == b1
        except Exception as exc:  # noqa: BLE001
            failures.append((i, utt, type(exc).__name__, str(exc)))
            if len(failures) >= 3:
                break
    assert not failures, failures[:3]


def test_p5_unsupported_profile_rejected():
    fr = SemanticFrame(speaker="user", act="ask", intent="query_price", polarity="pos")
    with pytest.raises(SaxilUnsupportedProfileError):
        encode(fr, profile="SAXIL_NATIVE_R2")


def test_p6_mutate_does_not_silently_accept_as_original():
    r = _rng()
    fr = _gen_frame(r)
    b = bytearray(encode(fr))
    if len(b) < 5:
        pytest.skip("short")
    # flip a payload byte after header
    b[4] ^= 0x5A
    try:
        obj = decode(bytes(b))
        # If decode somehow succeeds, re-encode must not equal original
        assert encode(obj) != bytes(encode(fr))
    except SaxilCoreError:
        pass  # expected fail-closed


def test_generation_metadata_recorded():
    # Evidence hook for reports
    assert SEED == 20261016
    assert N_CASES == 200
