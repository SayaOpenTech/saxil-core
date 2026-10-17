"""SAXIL W2 voice extension (packaged for saxil-core).

Frozen W1 remains in protocol.reference.
Research-only gold mappers (map_gold) are intentionally omitted from this package.
Scientific algorithm modules (codec/ast/dicts) are byte-identical to the research tree.
"""

from protocol.voice_extension.ast import Cmp, Date, Ent, Num, SemanticFrame, Time, VerbalUtt, VUnit
from protocol.voice_extension.codec import (
    MSG_SEMANTIC,
    MSG_VERBAL,
    W2_VERSION,
    canonical_bytes,
    decode_any,
    decode_w2,
    encode_w2,
)

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
    "encode_w2",
    "decode_w2",
    "decode_any",
    "canonical_bytes",
]
