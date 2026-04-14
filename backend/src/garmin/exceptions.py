from __future__ import annotations

# Unified exceptions live in adapter_protocol.py.
# Re-export here for backward compatibility (existing imports).
from src.garmin.adapter_protocol import (  # noqa: F401
    GarminAdapterError,
    GarminAuthError,
    GarminConnectionError,
    GarminNotFoundError,
    GarminRateLimitError,
)


class FormatterError(Exception):
    """Raised when the Garmin formatter encounters invalid input."""
