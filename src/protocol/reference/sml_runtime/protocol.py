"""SML protocol constants and AST (WORD / ROLE / BIND / FRAME / UPDATE). Frozen W1 v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

CODEBOOK = 50
N_ROLES = 6
ABSENT = -1
FIELD_SIZES = [8, 16, 8, 8, 2, 8]

MSG_FRAME = 1
MSG_UPDATE = 2
MSG_NESTED = 3
W1_VERSION = 1

ENV_VERSION = 1
KIND_SML = 1
KIND_JSON = 2
KIND_ACK = 3
KIND_REJECT = 4

STATUS_OK = 0
STATUS_ERR = 1
STATUS_UNSUPPORTED = 2
STATUS_BACKPRESSURE = 3


@dataclass
class SmlAst:
    msg_type: int
    roles: List[int]
    words: List[int]
    upd_roles: List[int] = field(default_factory=list)
    upd_words: List[int] = field(default_factory=list)

    def canonical_key(self) -> Tuple:
        return (
            self.msg_type,
            tuple(self.roles),
            tuple(self.words),
            tuple(self.upd_roles),
            tuple(self.upd_words),
        )


@dataclass
class Envelope:
    kind: int
    status: int
    message_id: int
    seq: int
    src_agent: int
    dst_agent: int
    payload: bytes
    env_version: int = ENV_VERSION
