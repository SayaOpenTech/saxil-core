"""saxil-core — SAXIL W2 codec SDK (0.1.0).

Distribution status: PUBLIC (Apache-2.0).
Does not include model weights, training stacks, or native token profiles.
"""

from __future__ import annotations

from saxil_core._version import (
    CODEC_PROFILE,
    DISTRIBUTION_STATUS,
    PROTOCOL_W2_VERSION,
    SOFTWARE_VERSION,
    SUPPORTED_PROFILES,
    get_version_info,
)
from saxil_core.errors import (
    SaxilCoreError,
    SaxilDecodeError,
    SaxilInvalidInputError,
    SaxilResourceLimitError,
    SaxilUnsupportedProfileError,
    SaxilUnsupportedVersionError,
    SaxilValidationError,
)
from saxil_core.w2 import (
    MSG_SEMANTIC,
    MSG_VERBAL,
    W2_VERSION,
    Cmp,
    Date,
    Ent,
    Num,
    SemanticFrame,
    Time,
    VerbalUtt,
    VUnit,
    canonical_bytes,
    decode,
    decode_any,
    decode_semantic,
    decode_verbal,
    decode_w2,
    encode,
    encode_semantic,
    encode_verbal,
    encode_w2,
    validate,
)

__all__ = [
    "SOFTWARE_VERSION",
    "PROTOCOL_W2_VERSION",
    "CODEC_PROFILE",
    "SUPPORTED_PROFILES",
    "DISTRIBUTION_STATUS",
    "get_version_info",
    "SaxilCoreError",
    "SaxilInvalidInputError",
    "SaxilDecodeError",
    "SaxilUnsupportedProfileError",
    "SaxilUnsupportedVersionError",
    "SaxilValidationError",
    "SaxilResourceLimitError",
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

__version__ = SOFTWARE_VERSION
