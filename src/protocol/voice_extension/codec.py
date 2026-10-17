"""SAXIL W2 codec: versioned byte extension of W1 for open voice values.

W1 v1 packets (byte0==1) are decoded by the frozen reference parser.
W2 packets (byte0==2) carry SEMANTIC / VERBAL messages.
Old W1 parsers reject W2 via VersionError — never silent mix-up.
"""

from __future__ import annotations

import struct
from typing import Any

from protocol.reference.sml_runtime.errors import DecodeError, VersionError
from protocol.reference.sml_runtime.parser import decode_w1
from protocol.voice_extension import dicts as D
from protocol.voice_extension.ast import Cmp, Date, Ent, Num, SemanticFrame, Time, VerbalUtt, VUnit

W2_VERSION = 2
MSG_SEMANTIC = 0x10
MSG_VERBAL = 0x11

MAX_PACKET = 4096
MAX_LITERAL = 96
MAX_SEQ = 64
MAX_FIELDS = 24
MAX_NEST = 8

TAG_SPEAKER = 0x01
TAG_ACT = 0x02
TAG_INTENT = 0x03
TAG_POLARITY = 0x04
TAG_ACTION = 0x05
TAG_OBJECT = 0x06
TAG_ATTR = 0x07
TAG_TIME = 0x08
TAG_AFFECT = 0x09
TAG_QTYPE = 0x0A
TAG_REQUEST = 0x0B
TAG_COND = 0x0C
TAG_KNOWN = 0x0D

KIND_NUM = 0x20
KIND_CUR = 0x21
KIND_DATE = 0x22
KIND_TIME = 0x23
KIND_ENT = 0x24
KIND_LIT = 0x26
KIND_CMP = 0x27
KIND_DIGITS = 0x28  # leading-zero / phone-like

OP_LEX_ID = 0x40
OP_LEX_LIT = 0x41
OP_NUM = 0x42
OP_CUR = 0x43
OP_DATE = 0x44
OP_TIME = 0x45
OP_NAME = 0x46
OP_ACR = 0x47
OP_PRON = 0x48
OP_PAUSE = 0x49
OP_EMPH = 0x4A


class W2Error(DecodeError):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code


def encode_varint(n: int) -> bytes:
    if n < 0:
        raise W2Error("invalid_enum", "varint unsigned")
    if n > 0xFFFFFFFF:
        raise W2Error("oversized", "integer exceeds uint32")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def decode_varint(buf: bytes, i: int) -> tuple[int, int]:
    n = 0
    shift = 0
    for _ in range(5):
        if i >= len(buf):
            raise W2Error("invalid_varint", "truncated")
        b = buf[i]
        i += 1
        n |= (b & 0x7F) << shift
        if not (b & 0x80):
            return n, i
        shift += 7
    raise W2Error("invalid_varint", "too long")


def _lit(s: str) -> bytes:
    raw = s.encode("utf-8")
    if len(raw) > MAX_LITERAL:
        raise W2Error("oversized", "literal")
    return bytes([len(raw)]) + raw


def _read_lit(buf: bytes, i: int) -> tuple[str, int]:
    if i >= len(buf):
        raise W2Error("unterminated_literal", "len")
    n = buf[i]
    i += 1
    if n > MAX_LITERAL:
        raise W2Error("oversized", "literal")
    if i + n > len(buf):
        raise W2Error("unterminated_literal", "body")
    try:
        s = buf[i : i + n].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise W2Error("invalid_enum", "utf8") from exc
    return s, i + n


def _enum_u8(table: tuple[str, ...], value: str | None) -> bytes:
    i = D.idx(table, value)
    if i is None:
        raise W2Error("invalid_enum", str(value))
    return bytes([i])


def _need(buf: bytes, i: int, n: int) -> None:
    if i + n > len(buf):
        raise W2Error("truncated", f"need {n}")


# --- value payloads ---

def encode_num(num: Num) -> bytes:
    unit_i = D.idx(D.CURRENCY, num.unit or "")
    if unit_i is None:
        raise W2Error("invalid_enum", f"currency {num.unit}")
    unit = unit_i
    if isinstance(num.v, str):
        d = "".join(ch for ch in num.v if ch.isdigit())
        raw = d.encode("ascii")
        if not raw or len(raw) > 16:
            raise W2Error("invalid_enum", "digits")
        return bytes([KIND_DIGITS, unit, len(raw)]) + raw
    return bytes([KIND_NUM, unit]) + encode_varint(int(num.v))


def encode_date(d: Date) -> bytes:
    if not (0 <= d.y <= 4095 and 0 <= d.mo <= 12 and 0 <= d.d <= 31):
        raise W2Error("invalid_date", f"{d.y}-{d.mo}-{d.d}")
    return bytes([KIND_DATE]) + struct.pack("!HBB", d.y, d.mo, d.d)


def encode_time(t: Time) -> bytes:
    flags = 0
    body = bytearray()
    if t.h is not None:
        if not (0 <= t.h <= 23):
            raise W2Error("invalid_time", "h")
        flags |= 1
        body.append(t.h)
    if t.m is not None:
        if not (0 <= t.m <= 59):
            raise W2Error("invalid_time", "m")
        flags |= 2
        body.append(t.m)
    if t.rel:
        flags |= 4
        body.extend(_enum_u8(D.REL, t.rel))
    if t.weekday:
        flags |= 8
        body.extend(_enum_u8(D.WEEKDAY, t.weekday))
    if t.unit:
        flags |= 16
        body.extend(_enum_u8(D.DUR_UNIT, t.unit))
    if t.v is not None:
        flags |= 32
        body.extend(encode_varint(int(t.v)))
    return bytes([KIND_TIME, flags]) + bytes(body)


def encode_ent(e: Ent) -> bytes:
    if not (1 <= e.eid <= 255):
        raise W2Error("invalid_reference", "eid")
    flags = 1 if e.name else 0
    out = bytearray([KIND_ENT, e.eid])
    out.extend(_enum_u8(D.ENT_TYPE, e.typ))
    out.extend(_enum_u8(D.REF, e.ref or ""))
    out.append(flags)
    if e.name:
        out.extend(_lit(e.name))
    return bytes(out)


def encode_value(val: Any) -> bytes:
    if isinstance(val, Num):
        return encode_num(val)
    if isinstance(val, Date):
        return encode_date(val)
    if isinstance(val, Time):
        return encode_time(val)
    if isinstance(val, Ent):
        return encode_ent(val)
    if isinstance(val, Cmp):
        return encode_cmp(val)
    if isinstance(val, int):
        return encode_num(Num(val))
    if isinstance(val, str):
        return bytes([KIND_LIT]) + _lit(val)
    raise W2Error("invalid_opcode", type(val).__name__)


def encode_cmp(c: Cmp) -> bytes:
    left = c.left.encode("ascii")
    if len(left) > 24:
        raise W2Error("oversized", "cmp left")
    right = c.right if isinstance(c.right, Num) else Num(c.right)
    return bytes([KIND_CMP]) + _enum_u8(D.CMP_OP, c.op) + bytes([len(left)]) + left + encode_num(right)


def decode_value(buf: bytes, i: int, depth: int = 0) -> tuple[Any, int]:
    if depth > MAX_NEST:
        raise W2Error("illegal_nesting", "depth")
    _need(buf, i, 1)
    kind = buf[i]
    i += 1
    if kind == KIND_NUM:
        _need(buf, i, 1)
        unit_i = buf[i]
        i += 1
        v, i = decode_varint(buf, i)
        unit = D.at(D.CURRENCY, unit_i) or None
        return Num(v, unit), i
    if kind == KIND_DIGITS:
        _need(buf, i, 2)
        unit_i, n = buf[i], buf[i + 1]
        i += 2
        _need(buf, i, n)
        digits = buf[i : i + n].decode("ascii")
        i += n
        unit = D.at(D.CURRENCY, unit_i) or None
        return Num(digits, unit), i
    if kind == KIND_DATE:
        _need(buf, i, 4)
        y, mo, d = struct.unpack("!HBB", buf[i : i + 4])
        if mo > 12 or d > 31:
            raise W2Error("invalid_date", f"{y}-{mo}-{d}")
        return Date(y, mo, d), i + 4
    if kind == KIND_TIME:
        _need(buf, i, 1)
        flags = buf[i]
        i += 1
        kw: dict[str, Any] = {}
        if flags & 1:
            _need(buf, i, 1)
            kw["h"] = buf[i]
            i += 1
            if kw["h"] > 23:
                raise W2Error("invalid_time", "h")
        if flags & 2:
            _need(buf, i, 1)
            kw["m"] = buf[i]
            i += 1
            if kw["m"] > 59:
                raise W2Error("invalid_time", "m")
        if flags & 4:
            _need(buf, i, 1)
            kw["rel"] = D.at(D.REL, buf[i]) or None
            i += 1
        if flags & 8:
            _need(buf, i, 1)
            kw["weekday"] = D.at(D.WEEKDAY, buf[i]) or None
            i += 1
        if flags & 16:
            _need(buf, i, 1)
            kw["unit"] = D.at(D.DUR_UNIT, buf[i]) or None
            i += 1
        if flags & 32:
            kw["v"], i = decode_varint(buf, i)
        return Time(**kw), i
    if kind == KIND_ENT:
        _need(buf, i, 4)
        eid, typ_i, ref_i, flags = buf[i], buf[i + 1], buf[i + 2], buf[i + 3]
        i += 4
        if eid < 1:
            raise W2Error("invalid_reference", "eid")
        name = None
        if flags & 1:
            name, i = _read_lit(buf, i)
        return Ent(eid, D.at(D.ENT_TYPE, typ_i), D.at(D.REF, ref_i) or None, name), i
    if kind == KIND_LIT:
        s, i = _read_lit(buf, i)
        return s, i
    if kind == KIND_CMP:
        _need(buf, i, 2)
        op = D.at(D.CMP_OP, buf[i])
        n = buf[i + 1]
        i += 2
        _need(buf, i, n)
        left = buf[i : i + n].decode("ascii")
        i += n
        right, i = decode_value(buf, i, depth + 1)
        if not isinstance(right, Num):
            raise W2Error("invalid_opcode", "cmp right")
        return Cmp(op, left, right), i
    if kind == KIND_CUR:
        _need(buf, i, 1)
        return D.at(D.CURRENCY, buf[i]) or None, i + 1
    raise W2Error("invalid_opcode", hex(kind))


def encode_semantic(frame: SemanticFrame) -> bytes:
    fields: list[tuple[int, bytes]] = [
        (TAG_SPEAKER, _enum_u8(D.SPEAKER, frame.speaker)),
        (TAG_ACT, _enum_u8(D.ACT, frame.act)),
        (TAG_INTENT, _enum_u8(D.INTENT, frame.intent)),
        (TAG_POLARITY, _enum_u8(D.POLARITY, frame.polarity)),
    ]
    if frame.action:
        fields.append((TAG_ACTION, _enum_u8(D.ACTION, frame.action)))
    if frame.object:
        fields.append((TAG_OBJECT, encode_ent(frame.object)))
    if frame.attribute is not None:
        attr = frame.attribute
        if isinstance(attr, (list, tuple)):
            blob = bytes([len(attr)]) + b"".join(encode_value(x) for x in attr)
            fields.append((TAG_ATTR, bytes([0x80]) + blob))  # 0x80 = list
        else:
            fields.append((TAG_ATTR, encode_value(attr)))
    if frame.time is not None:
        fields.append((TAG_TIME, encode_value(frame.time)))
    if frame.affect:
        fields.append((TAG_AFFECT, _enum_u8(D.AFFECT, frame.affect)))
    if frame.qtype:
        fields.append((TAG_QTYPE, _enum_u8(D.QTYPE, frame.qtype)))
    if frame.request:
        fields.append((TAG_REQUEST, _enum_u8(D.REQUEST, frame.request)))
    if frame.cond:
        fields.append((TAG_COND, encode_cmp(frame.cond)))
    if frame.known:
        if len(frame.known) > 8:
            raise W2Error("oversized", "known")
        blob = bytes([len(frame.known)]) + b"".join(encode_ent(e) for e in frame.known)
        fields.append((TAG_KNOWN, blob))
    fields.sort(key=lambda x: x[0])
    if len(fields) > MAX_FIELDS:
        raise W2Error("oversized", "fields")
    out = bytearray([W2_VERSION, MSG_SEMANTIC, len(fields)])
    for tag, payload in fields:
        out.append(tag)
        out.extend(payload)
    pkt = bytes(out)
    if len(pkt) > MAX_PACKET:
        raise W2Error("oversized", "packet")
    return pkt


def decode_semantic(buf: bytes) -> SemanticFrame:
    if len(buf) < 3:
        raise W2Error("truncated", "header")
    if buf[0] != W2_VERSION:
        raise VersionError(f"unsupported version {buf[0]}")
    if buf[1] != MSG_SEMANTIC:
        raise W2Error("unknown_msg_type", hex(buf[1]))
    n = buf[2]
    if n > MAX_FIELDS or n < 4:
        raise W2Error("invalid_length", "n_fields")
    i = 3
    got: dict[int, Any] = {}
    for _ in range(n):
        _need(buf, i, 1)
        tag = buf[i]
        i += 1
        if tag in got:
            raise W2Error("illegal_nesting", "dup tag")
        if tag in (TAG_SPEAKER, TAG_ACT, TAG_INTENT, TAG_POLARITY, TAG_ACTION, TAG_AFFECT, TAG_QTYPE, TAG_REQUEST):
            _need(buf, i, 1)
            table = {
                TAG_SPEAKER: D.SPEAKER,
                TAG_ACT: D.ACT,
                TAG_INTENT: D.INTENT,
                TAG_POLARITY: D.POLARITY,
                TAG_ACTION: D.ACTION,
                TAG_AFFECT: D.AFFECT,
                TAG_QTYPE: D.QTYPE,
                TAG_REQUEST: D.REQUEST,
            }[tag]
            got[tag] = D.at(table, buf[i])
            i += 1
        elif tag == TAG_OBJECT:
            ent, i = decode_value(buf, i)
            if not isinstance(ent, Ent):
                # encode_ent includes KIND_ENT prefix
                raise W2Error("invalid_opcode", "object")
            got[tag] = ent
        elif tag == TAG_ATTR:
            _need(buf, i, 1)
            if buf[i] == 0x80:
                i += 1
                _need(buf, i, 1)
                k = buf[i]
                i += 1
                items = []
                for _j in range(k):
                    v, i = decode_value(buf, i)
                    items.append(v)
                got[tag] = tuple(items)
            else:
                got[tag], i = decode_value(buf, i)
        elif tag == TAG_TIME:
            got[tag], i = decode_value(buf, i)
        elif tag == TAG_COND:
            c, i = decode_value(buf, i)
            if not isinstance(c, Cmp):
                raise W2Error("invalid_opcode", "cond")
            got[tag] = c
        elif tag == TAG_KNOWN:
            _need(buf, i, 1)
            k = buf[i]
            i += 1
            ents = []
            for _j in range(k):
                e, i = decode_value(buf, i)
                if not isinstance(e, Ent):
                    raise W2Error("invalid_opcode", "known")
                ents.append(e)
            got[tag] = tuple(ents)
        else:
            raise W2Error("invalid_opcode", hex(tag))
    if i != len(buf):
        raise W2Error("trailing_garbage", str(len(buf) - i))
    for req in (TAG_SPEAKER, TAG_ACT, TAG_INTENT, TAG_POLARITY):
        if req not in got:
            raise W2Error("invalid_length", "missing required")
    return SemanticFrame(
        speaker=got[TAG_SPEAKER],
        act=got[TAG_ACT],
        intent=got[TAG_INTENT],
        polarity=got[TAG_POLARITY],
        action=got.get(TAG_ACTION),
        object=got.get(TAG_OBJECT),
        attribute=got.get(TAG_ATTR),
        time=got.get(TAG_TIME),
        affect=got.get(TAG_AFFECT) or None,
        qtype=got.get(TAG_QTYPE) or None,
        request=got.get(TAG_REQUEST) or None,
        cond=got.get(TAG_COND),
        known=got.get(TAG_KNOWN) or (),
    )


def encode_unit(u: VUnit) -> bytes:
    if u.op == "LEX":
        j = D.idx(D.LEX, u.w or "")
        if j is not None:
            return bytes([OP_LEX_ID, j])
        return bytes([OP_LEX_LIT]) + _lit(u.w or "")
    if u.op == "NUM":
        mode = D.idx(D.NUM_MODE, u.mode or "cardinal")
        if mode is None:
            raise W2Error("invalid_enum", "mode")
        num = Num(u.v if u.v is not None else 0, u.unit)
        return bytes([OP_NUM, mode]) + encode_num(num)
    if u.op == "CUR":
        return bytes([OP_CUR]) + _enum_u8(D.CURRENCY, u.unit or "toman")
    if u.op == "DATE":
        return bytes([OP_DATE]) + encode_date(Date(u.y or 0, u.mo or 0, u.d or 0))[1:]
    if u.op == "TIME":
        blob = encode_time(Time(h=u.h, m=u.m, rel=u.rel, weekday=u.weekday, unit=u.unit, v=u.v if isinstance(u.v, int) else None))
        return bytes([OP_TIME]) + blob[1:]
    if u.op == "NAME":
        return bytes([OP_NAME]) + _lit(u.w or "")
    if u.op == "ACR":
        return bytes([OP_ACR]) + _lit(u.w or "") + _lit(u.spoken or "")
    if u.op == "PRON":
        return bytes([OP_PRON]) + _lit(u.w or "") + _lit(u.spoken or "")
    if u.op == "PAUSE":
        return bytes([OP_PAUSE]) + _enum_u8(D.PAUSE, u.pause or "short")
    if u.op == "EMPH":
        return bytes([OP_EMPH]) + _lit(u.w or "")
    raise W2Error("invalid_opcode", u.op)


def decode_unit(buf: bytes, i: int) -> tuple[VUnit, int]:
    _need(buf, i, 1)
    op = buf[i]
    i += 1
    if op == OP_LEX_ID:
        _need(buf, i, 1)
        return VUnit("LEX", w=D.at(D.LEX, buf[i])), i + 1
    if op == OP_LEX_LIT:
        w, i = _read_lit(buf, i)
        return VUnit("LEX", w=w), i
    if op == OP_NUM:
        _need(buf, i, 1)
        mode = D.at(D.NUM_MODE, buf[i])
        i += 1
        num, i = decode_value(buf, i)
        if not isinstance(num, Num):
            raise W2Error("invalid_opcode", "num")
        return VUnit("NUM", v=num.v, unit=num.unit, mode=mode), i
    if op == OP_CUR:
        _need(buf, i, 1)
        return VUnit("CUR", unit=D.at(D.CURRENCY, buf[i]) or None), i + 1
    if op == OP_DATE:
        _need(buf, i, 4)
        y, mo, d = struct.unpack("!HBB", buf[i : i + 4])
        if mo > 12 or d > 31:
            raise W2Error("invalid_date", f"{y}-{mo}-{d}")
        return VUnit("DATE", y=y, mo=mo, d=d), i + 4
    if op == OP_TIME:
        t, j = decode_value(bytes([KIND_TIME]) + buf[i:], 0)
        consumed = j - 1
        i += consumed
        assert isinstance(t, Time)
        return VUnit("TIME", h=t.h, m=t.m, rel=t.rel, weekday=t.weekday, unit=t.unit, v=t.v), i
    if op == OP_NAME:
        w, i = _read_lit(buf, i)
        return VUnit("NAME", w=w), i
    if op == OP_ACR:
        w, i = _read_lit(buf, i)
        spoken, i = _read_lit(buf, i)
        return VUnit("ACR", w=w, spoken=spoken or None), i
    if op == OP_PRON:
        w, i = _read_lit(buf, i)
        spoken, i = _read_lit(buf, i)
        return VUnit("PRON", w=w, spoken=spoken), i
    if op == OP_PAUSE:
        _need(buf, i, 1)
        return VUnit("PAUSE", pause=D.at(D.PAUSE, buf[i])), i + 1
    if op == OP_EMPH:
        w, i = _read_lit(buf, i)
        return VUnit("EMPH", w=w), i
    raise W2Error("invalid_opcode", hex(op))


def encode_verbal(utt: VerbalUtt) -> bytes:
    if not utt.units or len(utt.units) > MAX_SEQ:
        raise W2Error("invalid_length", "seq")
    out = bytearray([W2_VERSION, MSG_VERBAL])
    out.extend(_enum_u8(D.UTT_TYPE, utt.utt_type))
    out.append(len(utt.units))
    for u in utt.units:
        out.extend(encode_unit(u))
    pkt = bytes(out)
    if len(pkt) > MAX_PACKET:
        raise W2Error("oversized", "packet")
    return pkt


def decode_verbal(buf: bytes) -> VerbalUtt:
    if len(buf) < 4:
        raise W2Error("truncated", "header")
    if buf[0] != W2_VERSION:
        raise VersionError(f"unsupported version {buf[0]}")
    if buf[1] != MSG_VERBAL:
        raise W2Error("unknown_msg_type", hex(buf[1]))
    utt_type = D.at(D.UTT_TYPE, buf[2])
    n = buf[3]
    if n < 1 or n > MAX_SEQ:
        raise W2Error("invalid_length", "seq")
    i = 4
    units = []
    for _ in range(n):
        u, i = decode_unit(buf, i)
        units.append(u)
    if i != len(buf):
        raise W2Error("trailing_garbage", str(len(buf) - i))
    return VerbalUtt(utt_type, tuple(units))


def encode_w2(obj: SemanticFrame | VerbalUtt) -> bytes:
    if isinstance(obj, SemanticFrame):
        return encode_semantic(obj)
    if isinstance(obj, VerbalUtt):
        return encode_verbal(obj)
    raise W2Error("invalid_opcode", type(obj).__name__)


def decode_w2(buf: bytes) -> SemanticFrame | VerbalUtt:
    if not buf:
        raise W2Error("truncated", "empty")
    if len(buf) > MAX_PACKET:
        raise W2Error("oversized", "packet")
    if buf[0] == 1:
        raise VersionError("W1 packet; use decode_any")
    if buf[0] != W2_VERSION:
        raise VersionError(f"unsupported version {buf[0]}")
    if len(buf) < 2:
        raise W2Error("truncated", "type")
    if buf[1] == MSG_SEMANTIC:
        return decode_semantic(buf)
    if buf[1] == MSG_VERBAL:
        return decode_verbal(buf)
    raise W2Error("unknown_msg_type", hex(buf[1]))


def decode_any(buf: bytes):
    """New decoder: W1 v1 → SmlAst; W2 → SemanticFrame/VerbalUtt."""
    if not buf:
        raise W2Error("truncated", "empty")
    if buf[0] == 1:
        return decode_w1(buf)
    if buf[0] == 2:
        return decode_w2(buf)
    raise VersionError(f"unsupported version {buf[0]}")


def canonical_bytes(obj: SemanticFrame | VerbalUtt) -> bytes:
    return encode_w2(obj)
