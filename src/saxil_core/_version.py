"""Software / protocol / profile identity (layered; see VERSIONING_POLICY)."""

from __future__ import annotations

from typing import Any

SOFTWARE_VERSION = "0.1.0"
PROTOCOL_W2_VERSION = 2  # wire byte0 for W2
CODEC_PROFILE = "W2-v1"
SUPPORTED_PROFILES = ("W2-v1",)
DISTRIBUTION_STATUS = "PUBLIC"
# Readable S/V and Native profiles are not part of this Core package surface.
DEFERRED_PROFILES = (
    "S0.1",
    "V0.1",
    "SAXIL_NATIVE_R2",
    "SV2-ARM-B",
)


def get_version_info() -> dict[str, Any]:
    return {
        "software_version": SOFTWARE_VERSION,
        "protocol_w2_version": PROTOCOL_W2_VERSION,
        "codec_profile": CODEC_PROFILE,
        "supported_profiles": list(SUPPORTED_PROFILES),
        "deferred_profiles": list(DEFERRED_PROFILES),
        "distribution_status": DISTRIBUTION_STATUS,
        "import_name": "saxil_core",
        "package_name": "saxil-core",
    }
