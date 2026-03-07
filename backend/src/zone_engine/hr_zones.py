from __future__ import annotations

from src.zone_engine.constants import (
    COGGAN_HR_ZONE_NAMES,
    COGGAN_HR_ZONES,
    FRIEL_HR_ZONE_NAMES,
    FRIEL_HR_ZONES,
    PCT_HRR_ZONE_NAMES,
    PCT_HRR_ZONES,
    PCT_MAX_HR_ZONE_NAMES,
    PCT_MAX_HR_ZONES,
)
from src.zone_engine.exceptions import ZoneValidationError
from src.zone_engine.models import Zone, ZoneConfig, ZoneSet


class HRZoneCalculator:
    """Calculates HR training zones from a ZoneConfig.

    Supports methods: "coggan", "friel", "pct_max_hr", "pct_hrr".
    Pure computation — no I/O.
    """

    def __init__(self, config: ZoneConfig) -> None:
        self._config = config

    def calculate(self) -> ZoneSet:
        """Calculate and return a ZoneSet based on the configured method.

        Raises ZoneValidationError for invalid threshold values.
        """
        method = self._config.method

        if method == "coggan":
            return self._calculate_from_lthr(COGGAN_HR_ZONES, COGGAN_HR_ZONE_NAMES)
        elif method == "friel":
            return self._calculate_from_lthr(FRIEL_HR_ZONES, FRIEL_HR_ZONE_NAMES)
        elif method == "pct_max_hr":
            return self._calculate_from_max_hr()
        elif method == "pct_hrr":
            return self._calculate_karvonen()
        else:
            raise ZoneValidationError(f"Unknown HR zone method: {method!r}")

    def _validate_threshold(self, value: float, label: str = "threshold") -> None:
        if value <= 0:
            raise ZoneValidationError(
                f"{label} must be positive; got {value}."
            )

    def _calculate_from_lthr(
        self,
        pct_table: list[tuple[float, float]],
        names: list[str],
    ) -> ZoneSet:
        lthr = self._config.threshold
        self._validate_threshold(lthr, "LTHR")

        zones: list[Zone] = []
        for i, (pct_lower, pct_upper) in enumerate(pct_table):
            zones.append(
                Zone(
                    zone_number=i + 1,
                    name=names[i],
                    lower=lthr * pct_lower,
                    upper=lthr * pct_upper,
                    pct_lower=pct_lower,
                    pct_upper=pct_upper,
                )
            )
        return ZoneSet(config=self._config, zones=zones)

    def _calculate_from_max_hr(self) -> ZoneSet:
        max_hr = self._config.max_value if self._config.max_value > 0 else self._config.threshold
        self._validate_threshold(max_hr, "max_hr")

        zones: list[Zone] = []
        for i, (pct_lower, pct_upper) in enumerate(PCT_MAX_HR_ZONES):
            zones.append(
                Zone(
                    zone_number=i + 1,
                    name=PCT_MAX_HR_ZONE_NAMES[i],
                    lower=max_hr * pct_lower,
                    upper=max_hr * pct_upper,
                    pct_lower=pct_lower,
                    pct_upper=pct_upper,
                )
            )
        return ZoneSet(config=self._config, zones=zones)

    def _calculate_karvonen(self) -> ZoneSet:
        max_hr = self._config.max_value if self._config.max_value > 0 else self._config.threshold
        resting_hr = self._config.resting_value
        self._validate_threshold(max_hr, "max_hr")
        if resting_hr <= 0:
            raise ZoneValidationError(
                f"resting_hr must be positive; got {resting_hr}."
            )

        hrr = max_hr - resting_hr

        zones: list[Zone] = []
        for i, (pct_lower, pct_upper) in enumerate(PCT_HRR_ZONES):
            zones.append(
                Zone(
                    zone_number=i + 1,
                    name=PCT_HRR_ZONE_NAMES[i],
                    lower=resting_hr + pct_lower * hrr,
                    upper=resting_hr + pct_upper * hrr,
                    pct_lower=pct_lower,
                    pct_upper=pct_upper,
                )
            )
        return ZoneSet(config=self._config, zones=zones)
