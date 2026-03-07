from __future__ import annotations

from src.zone_engine.constants import DANIELS_PACE_ZONE_NAMES, DANIELS_PACE_ZONES
from src.zone_engine.exceptions import ZoneValidationError
from src.zone_engine.models import Zone, ZoneConfig, ZoneSet


def format_pace(seconds: int | float) -> str:
    """Convert a pace in seconds per km to a "M:SS" string.

    Example: 270 → "4:30"
    """
    total_seconds = int(seconds)
    minutes, secs = divmod(total_seconds, 60)
    return f"{minutes}:{secs:02d}"


class PaceZoneCalculator:
    """Calculates pace training zones from a ZoneConfig.

    Supports methods: "pct_threshold".
    Pace zones use sec/km — higher value means slower pace.
    Pure computation — no I/O.
    """

    def __init__(self, config: ZoneConfig) -> None:
        self._config = config

    def calculate(self) -> ZoneSet:
        """Calculate and return a ZoneSet based on the configured method.

        Raises ZoneValidationError for invalid threshold values.
        """
        method = self._config.method

        if method == "pct_threshold":
            return self._calculate_from_threshold()
        else:
            raise ZoneValidationError(f"Unknown pace zone method: {method!r}")

    def _validate_threshold(self, value: float) -> None:
        if value <= 0:
            raise ZoneValidationError(
                f"threshold_pace must be positive; got {value}."
            )

    def _calculate_from_threshold(self) -> ZoneSet:
        threshold = self._config.threshold
        self._validate_threshold(threshold)

        zones: list[Zone] = []
        for i, (pct_lower, pct_upper) in enumerate(DANIELS_PACE_ZONES):
            # pct_lower > pct_upper because slower pace (lower boundary) has
            # a higher percentage multiplier than the faster boundary
            zones.append(
                Zone(
                    zone_number=i + 1,
                    name=DANIELS_PACE_ZONE_NAMES[i],
                    lower=threshold * pct_lower,
                    upper=threshold * pct_upper,
                    pct_lower=pct_lower,
                    pct_upper=pct_upper,
                )
            )
        return ZoneSet(config=self._config, zones=zones)
