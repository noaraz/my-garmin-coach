from __future__ import annotations

from dataclasses import dataclass, field

from src.zone_engine.exceptions import ZoneValidationError

_VALID_ZONE_RANGE = range(1, 6)  # zones 1–5


@dataclass
class Zone:
    """A single training zone with absolute and percentage boundaries."""

    zone_number: int
    name: str
    lower: float
    upper: float
    pct_lower: float
    pct_upper: float


@dataclass
class ZoneConfig:
    """Configuration used to calculate a set of zones."""

    threshold: float
    method: str
    max_value: float = 0.0
    resting_value: float = 0.0


@dataclass
class ZoneSet:
    """An ordered collection of 5 zones produced from a ZoneConfig."""

    config: ZoneConfig
    zones: list[Zone] = field(default_factory=list)

    def get_zone(self, zone_number: int) -> Zone:
        """Return the Zone for a given zone number (1–5).

        Raises ZoneValidationError if zone_number is out of range.
        """
        if zone_number not in _VALID_ZONE_RANGE:
            raise ZoneValidationError(
                f"Zone number {zone_number} is out of range; must be 1–5."
            )
        for zone in self.zones:
            if zone.zone_number == zone_number:
                return zone
        raise ZoneValidationError(
            f"Zone {zone_number} not found in this ZoneSet."
        )
