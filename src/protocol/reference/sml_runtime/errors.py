"""SML runtime errors. Frozen W1 v1 reference copy."""


class SmlError(Exception):
    """Base error."""


class DecodeError(SmlError):
    """Malformed or unsupported SML / envelope packet."""


class TransportError(SmlError):
    """Transport / framing failure."""


class VersionError(DecodeError):
    """Unsupported protocol version."""


class BackpressureError(TransportError):
    """Queue full / producer rejected."""
