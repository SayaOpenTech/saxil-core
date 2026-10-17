"""SML W0/W1 binary compilers. Frozen W1 v1 reference copy."""

from __future__ import annotations

from .errors import DecodeError, VersionError  # noqa: F401
from .protocol import CODEBOOK, MSG_FRAME, MSG_NESTED, MSG_UPDATE, W1_VERSION, SmlAst


def encode_w0(ast: SmlAst) -> bytes:
    if ast.msg_type != MSG_FRAME:
        raise ValueError("W0 only encodes FRAME")
    mask = 0
    words = []
    role_to_word = {r: w for r, w in zip(ast.roles, ast.words)}
    for r in range(6):
        if r in role_to_word:
            mask |= 1 << r
            words.append(int(role_to_word[r]) & 0xFF)
    return bytes([mask] + words)


def encode_w1(ast: SmlAst) -> bytes:
    if ast.msg_type not in (MSG_FRAME, MSG_UPDATE, MSG_NESTED):
        raise ValueError("bad type")
    mask = 0
    role_to_word = {r: w for r, w in zip(ast.roles, ast.words)}
    words = []
    for r in range(6):
        if r in role_to_word:
            mask |= 1 << r
            words.append(int(role_to_word[r]) & 0xFF)
    n_upd = len(ast.upd_roles)
    if ast.msg_type == MSG_FRAME and n_upd:
        raise ValueError("FRAME cannot have updates")
    if ast.msg_type == MSG_UPDATE and n_upd != 1:
        raise ValueError("UPDATE needs 1 upd")
    if ast.msg_type == MSG_NESTED and n_upd != 2:
        raise ValueError("NESTED needs 2 upd")
    flags = ((n_upd & 0xF) << 4) | (len(words) & 0xF)
    out = bytearray([W1_VERSION, ast.msg_type, mask, flags])
    out.extend(words)
    for ur, uw in zip(ast.upd_roles, ast.upd_words):
        if not (0 <= ur < 6) or uw >= CODEBOOK:
            raise ValueError("bad update bind")
        out.append(ur & 0xFF)
        out.append(uw & 0xFF)
    return bytes(out)


def encode_sml(ast: SmlAst, fmt: str = "w1") -> bytes:
    if fmt == "w0":
        return encode_w0(ast)
    if fmt == "w1":
        return encode_w1(ast)
    raise ValueError(f"unknown format {fmt}")
