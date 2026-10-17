"""Optional S/V surface — deferred in Core 0.1.0.

S0.1 / V0.1 are semantic/lossy relative to Persian text. They are intentionally
not bundled in saxil-core W2 packages to keep Core free of research-path and
TTS-prep coupling.

Importing helpers from this module raises an explicit unsupported-profile error.
"""

from __future__ import annotations

from saxil_core.errors import SaxilUnsupportedProfileError

_MSG = (
    "S0.1/V0.1 adapters are deferred from saxil-core 0.1.0. "
    "They are not part of the public Core surface. "
    "Do not treat Persian text round-trips as lossless W2 behavior."
)


def encode(*_args, **_kwargs):  # noqa: ANN001
    raise SaxilUnsupportedProfileError("unsupported_profile", _MSG)


def decode(*_args, **_kwargs):  # noqa: ANN001
    raise SaxilUnsupportedProfileError("unsupported_profile", _MSG)


def available() -> bool:
    return False
