"""SML W0/W1 parsers. Frozen W1 v1 reference copy."""

from __future__ import annotations

from .errors import DecodeError, VersionError
from .protocol import CODEBOOK, MSG_FRAME, MSG_NESTED, MSG_UPDATE, W1_VERSION, SmlAst


def decode_w0(pkt: bytes) -> SmlAst:
    if not pkt:
        raise DecodeError("empty")
    mask = pkt[0]
    roles, words = [], []
    i = 1
    for r in range(6):
        if mask & (1 << r):
            if i >= len(pkt):
                raise DecodeError("truncate")
            w = pkt[i]
            if w >= CODEBOOK:
                raise DecodeError("bad word")
            roles.append(r)
            words.append(w)
            i += 1
    if i != len(pkt):
        raise DecodeError("trailing")
    if mask == 0 or not roles:
        raise DecodeError("empty mask")
    return SmlAst(MSG_FRAME, roles, words)


def decode_w1(pkt: bytes) -> SmlAst:
    if len(pkt) < 4:
        raise DecodeError("truncate header")
    ver, typ, mask, flags = pkt[0], pkt[1], pkt[2], pkt[3]
    if ver != W1_VERSION:
        raise VersionError(f"unsupported W1 version {ver}")
    if typ not in (MSG_FRAME, MSG_UPDATE, MSG_NESTED):
        raise DecodeError("bad type")
    n_bind = flags & 0xF
    n_upd = (flags >> 4) & 0xF
    roles, words = [], []
    i = 4
    for r in range(6):
        if mask & (1 << r):
            if i >= len(pkt):
                raise DecodeError("truncate words")
            w = pkt[i]
            if w >= CODEBOOK:
                raise DecodeError("bad word")
            roles.append(r)
            words.append(w)
            i += 1
    if len(roles) != n_bind:
        raise DecodeError("bind count mismatch")
    if typ == MSG_FRAME and n_upd != 0:
        raise DecodeError("FRAME n_upd")
    if typ == MSG_UPDATE and n_upd != 1:
        raise DecodeError("UPDATE n_upd")
    if typ == MSG_NESTED and n_upd != 2:
        raise DecodeError("NESTED n_upd")
    upd_roles, upd_words = [], []
    for _ in range(n_upd):
        if i + 1 >= len(pkt):
            raise DecodeError("truncate upd")
        ur, uw = pkt[i], pkt[i + 1]
        i += 2
        if ur >= 6 or uw >= CODEBOOK:
            raise DecodeError("bad upd")
        upd_roles.append(ur)
        upd_words.append(uw)
    if i != len(pkt):
        raise DecodeError("trailing")
    if not roles:
        raise DecodeError("empty frame")
    return SmlAst(typ, roles, words, upd_roles, upd_words)


def decode_sml(pkt: bytes, fmt: str = "w1") -> SmlAst:
    if fmt == "w0":
        return decode_w0(pkt)
    if fmt == "w1":
        return decode_w1(pkt)
    raise ValueError(f"unknown format {fmt}")
