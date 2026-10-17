"""Authoritative conformance vectors (independent + compatibility-only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from saxil_core import (
    Cmp,
    Date,
    Ent,
    Num,
    SemanticFrame,
    Time,
    VerbalUtt,
    VUnit,
    decode,
    encode,
)
from saxil_core.errors import (
    SaxilCoreError,
    SaxilDecodeError,
    SaxilResourceLimitError,
    SaxilUnsupportedVersionError,
)

VEC_PATH = Path(__file__).resolve().parents[1] / "conformance" / "INDEPENDENT_CONFORMANCE_VECTORS.json"


def _load():
    return json.loads(VEC_PATH.read_text(encoding="utf-8"))


def _ast_from(obj: dict):
    kind = obj.get("type")
    if kind == "semantic":
        known = tuple(
            Ent(eid=int(e["eid"]), typ=e["typ"], ref=e.get("ref"), name=e.get("name"))
            for e in (obj.get("known") or [])
        )
        cond = None
        if obj.get("cond"):
            c = obj["cond"]
            right = c["right"]
            if isinstance(right, dict):
                right = Num(v=right["v"], unit=right.get("unit"))
            cond = Cmp(op=c["op"], left=c["left"], right=right)
        obj_ent = None
        if obj.get("object"):
            o = obj["object"]
            obj_ent = Ent(eid=int(o["eid"]), typ=o["typ"], ref=o.get("ref"), name=o.get("name"))
        t = obj.get("time")
        time_v = None
        if isinstance(t, dict):
            if "y" in t:
                time_v = Date(y=int(t["y"]), mo=int(t["mo"]), d=int(t["d"]))
            else:
                time_v = Time(**{k: t.get(k) for k in ("h", "m", "rel", "weekday", "unit", "v")})
        attr = obj.get("attribute")
        if isinstance(attr, dict) and attr.get("kind") == "num":
            attr = Num(v=attr["v"], unit=attr.get("unit"))
        return SemanticFrame(
            speaker=obj.get("speaker", "user"),
            act=obj["act"],
            intent=obj["intent"],
            polarity=obj.get("polarity", "pos"),
            action=obj.get("action"),
            object=obj_ent,
            attribute=attr,
            time=time_v,
            affect=obj.get("affect"),
            qtype=obj.get("qtype"),
            request=obj.get("request"),
            cond=cond,
            known=known,
            modality=obj.get("modality"),
            uncertainty=obj.get("uncertainty"),
        )
    if kind == "verbal":
        units = []
        for u in obj.get("units") or []:
            units.append(
                VUnit(
                    op=u["op"],
                    w=u.get("w"),
                    v=u.get("v"),
                    unit=u.get("unit"),
                    spoken=u.get("spoken"),
                    mode=u.get("mode"),
                    y=u.get("y"),
                    mo=u.get("mo"),
                    d=u.get("d"),
                    h=u.get("h"),
                    m=u.get("m"),
                    rel=u.get("rel"),
                    weekday=u.get("weekday"),
                    pause=u.get("pause"),
                )
            )
        return VerbalUtt(utt_type=obj.get("utt_type", "statement"), units=tuple(units))
    raise AssertionError(f"unknown ast type {kind}")


def _materialize_hex(v: dict) -> bytes:
    if "encoded_hex" in v:
        hx = v["encoded_hex"]
        return bytes.fromhex(hx) if hx else b""
    gen = v.get("encoded_hex_generator")
    if gen:
        prefix = bytes.fromhex(gen["prefix_hex"])
        pad = int(gen["pad_byte"], 16)
        total = int(gen["total_len"])
        return prefix + bytes([pad]) * (total - len(prefix))
    raise AssertionError("no encoded payload")


@pytest.fixture(scope="module")
def catalog():
    return _load()


def test_catalog_has_independent_and_invalid(catalog):
    inds = [v for v in catalog["vectors"] if v.get("evidence_class") == "INDEPENDENT"]
    assert len(inds) >= 16
    assert any(v["class"] == "valid" for v in inds)
    assert any(v["class"] == "invalid" for v in inds)
    cats = {v.get("category") for v in inds if v.get("category")}
    assert {"ENT", "NUM", "DATE", "CMP"}.issubset(cats)


def _valid_vector_ids(catalog):
    return [
        v["id"]
        for v in catalog["vectors"]
        if v["class"] == "valid" and "expected_hex" in v and "ast" in v
    ]


def _invalid_vector_ids(catalog):
    return [v["id"] for v in catalog["vectors"] if v["class"] == "invalid"]


@pytest.mark.parametrize(
    "vid",
    [
        "WV-IND-001",
        "WV-IND-002",
        "WV-IND-003",
        "WV-IND-004",
        "WV-IND-005",
        "WV-IND-ENT-001",
        "WV-IND-ENT-002",
        "WV-IND-NUM-001",
        "WV-IND-NUM-002",
        "WV-IND-NUM-003",
        "WV-IND-DATE-001",
        "WV-IND-CMP-001",
        "WV-COMPAT-001",
        "WV-COMPAT-ENT-001",
    ],
)
def test_valid_vector_encode_matches_expected(catalog, vid):
    v = next(x for x in catalog["vectors"] if x["id"] == vid)
    assert v["class"] == "valid"
    ast = _ast_from(v["ast"])
    got = encode(ast).hex()
    assert got == v["expected_hex"], f"{vid}: {got} != {v['expected_hex']}"
    # decode expected bytes must re-encode identically
    obj = decode(bytes.fromhex(v["expected_hex"]))
    assert encode(obj).hex() == v["expected_hex"]


@pytest.mark.parametrize(
    "vid",
    [
        "WV-IND-N01",
        "WV-IND-N02",
        "WV-IND-N03",
        "WV-IND-N04",
        "WV-IND-N05",
        "WV-IND-N06",
        "WV-IND-ENT-N01",
        "WV-IND-DATE-N01",
        "WV-IND-CMP-N01",
    ],
)
def test_invalid_vector_rejects(catalog, vid):
    v = next(x for x in catalog["vectors"] if x["id"] == vid)
    assert v["class"] == "invalid"
    payload = _materialize_hex(v)
    with pytest.raises(
        (SaxilDecodeError, SaxilUnsupportedVersionError, SaxilResourceLimitError, SaxilCoreError)
    ) as ei:
        decode(payload)
    code = getattr(ei.value, "code", "") or ""
    blob = f"{code}:{ei.value}".lower()
    assert any(c.lower() in blob for c in v["expected_error_codes"]), blob


def test_num_negative_rejected_on_encode():
    """Unsigned varint contract: negative magnitudes MUST NOT encode."""
    with pytest.raises(SaxilCoreError):
        encode(
            SemanticFrame(
                speaker="user",
                act="ask",
                intent="query_price",
                polarity="pos",
                attribute=Num(v=-1),
            )
        )
