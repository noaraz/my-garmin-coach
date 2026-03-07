from __future__ import annotations


class FormatterError(Exception):
    """Raised when the Garmin formatter encounters invalid input."""


class GarminAuthError(Exception):
    """Raised when authentication with Garmin Connect fails."""


class GarminRateLimitError(Exception):
    """Raised when Garmin Connect returns a rate-limit (429) response."""
