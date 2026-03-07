from __future__ import annotations

import pytest

from src.zone_engine.exceptions import ZoneValidationError
from src.zone_engine.models import Zone, ZoneConfig, ZoneSet
from src.zone_engine.pace_zones import PaceZoneCalculator, format_pace


class TestFromThreshold:
    """test_from_threshold: 270s/km, method=pct_threshold → 5 zones correct"""

    def test_from_threshold_returns_five_zones(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=270.0, method="pct_threshold")
        calc = PaceZoneCalculator(config)

        # Act
        zone_set = calc.calculate()

        # Assert
        assert len(zone_set.zones) == 5

    def test_from_threshold_zone1_boundaries(self) -> None:
        # Arrange
        # Zone 1: 129–114% of threshold pace (slower = higher sec/km)
        # lower bound = 129% of 270 = 348.3; upper bound = 114% of 270 = 307.8
        config = ZoneConfig(threshold=270.0, method="pct_threshold")
        calc = PaceZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone1 = zone_set.get_zone(1)

        # Assert (lower = slower/higher sec/km boundary, upper = faster boundary)
        assert zone1.lower == pytest.approx(270.0 * 1.29, rel=1e-3)
        assert zone1.upper == pytest.approx(270.0 * 1.14, rel=1e-3)

    def test_from_threshold_zone5_boundaries(self) -> None:
        # Arrange
        # Zone 5: 97–90% of threshold pace
        # lower = 97% of 270 = 261.9; upper = 90% of 270 = 243.0
        config = ZoneConfig(threshold=270.0, method="pct_threshold")
        calc = PaceZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone5 = zone_set.get_zone(5)

        # Assert
        assert zone5.lower == pytest.approx(270.0 * 0.97, rel=1e-3)
        assert zone5.upper == pytest.approx(270.0 * 0.90, rel=1e-3)

    def test_from_threshold_zone3_boundaries(self) -> None:
        # Arrange
        # Zone 3: 106–100% of threshold pace
        config = ZoneConfig(threshold=270.0, method="pct_threshold")
        calc = PaceZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone3 = zone_set.get_zone(3)

        # Assert
        assert zone3.lower == pytest.approx(270.0 * 1.06, rel=1e-3)
        assert zone3.upper == pytest.approx(270.0 * 1.00, rel=1e-3)


class TestCustomPaceZones:
    """test_custom: explicit boundaries → stored as-is"""

    def test_custom_pace_zones_stored_as_is(self) -> None:
        # Arrange
        custom_zones = [
            Zone(zone_number=1, name="Z1", lower=360.0, upper=330.0, pct_lower=0.0, pct_upper=0.0),
            Zone(zone_number=2, name="Z2", lower=330.0, upper=310.0, pct_lower=0.0, pct_upper=0.0),
            Zone(zone_number=3, name="Z3", lower=310.0, upper=290.0, pct_lower=0.0, pct_upper=0.0),
            Zone(zone_number=4, name="Z4", lower=290.0, upper=270.0, pct_lower=0.0, pct_upper=0.0),
            Zone(zone_number=5, name="Z5", lower=270.0, upper=250.0, pct_lower=0.0, pct_upper=0.0),
        ]
        config = ZoneConfig(threshold=0.0, method="custom")
        zone_set = ZoneSet(config=config, zones=custom_zones)

        # Act & Assert — exact values stored
        assert zone_set.get_zone(1).lower == 360.0
        assert zone_set.get_zone(1).upper == 330.0
        assert zone_set.get_zone(5).upper == 250.0


class TestRecalculateOnChange:
    """test_recalculate_on_change: threshold 270→265 → all zones shift"""

    def test_recalculate_zones_shift_on_threshold_decrease(self) -> None:
        # Arrange
        config_270 = ZoneConfig(threshold=270.0, method="pct_threshold")
        config_265 = ZoneConfig(threshold=265.0, method="pct_threshold")
        calc_270 = PaceZoneCalculator(config_270)
        calc_265 = PaceZoneCalculator(config_265)

        # Act
        zones_270 = calc_270.calculate()
        zones_265 = calc_265.calculate()

        # Assert — faster threshold means faster (lower sec/km) zones
        for i in range(1, 6):
            assert zones_265.get_zone(i).lower < zones_270.get_zone(i).lower
            assert zones_265.get_zone(i).upper < zones_270.get_zone(i).upper


class TestSlowerMeansHigherSeconds:
    """test_slower_means_higher_seconds: zone 1 vs zone 5 → zone 1 higher sec/km"""

    def test_zone1_lower_slower_than_zone5_lower(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=270.0, method="pct_threshold")
        calc = PaceZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone1 = zone_set.get_zone(1)
        zone5 = zone_set.get_zone(5)

        # Assert — Zone 1 (easy/recovery) is slower = higher sec/km
        assert zone1.lower > zone5.lower

    def test_zone1_upper_slower_than_zone5_upper(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=270.0, method="pct_threshold")
        calc = PaceZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone1 = zone_set.get_zone(1)
        zone5 = zone_set.get_zone(5)

        # Assert
        assert zone1.upper > zone5.upper


class TestRejectsZero:
    """test_rejects_zero: threshold=0 → ValidationError"""

    def test_rejects_zero_threshold(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ZoneValidationError):
            config = ZoneConfig(threshold=0.0, method="pct_threshold")
            calc = PaceZoneCalculator(config)
            calc.calculate()

    def test_rejects_negative_threshold(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ZoneValidationError):
            config = ZoneConfig(threshold=-10.0, method="pct_threshold")
            calc = PaceZoneCalculator(config)
            calc.calculate()


class TestFormattingHelper:
    """test_formatting_helper: 270 sec/km → "4:30" string"""

    def test_format_pace_270_returns_4_30(self) -> None:
        # Arrange & Act
        result = format_pace(270)

        # Assert
        assert result == "4:30"

    def test_format_pace_60_returns_1_00(self) -> None:
        # Arrange & Act
        result = format_pace(60)

        # Assert
        assert result == "1:00"

    def test_format_pace_305_returns_5_05(self) -> None:
        # Arrange & Act
        result = format_pace(305)

        # Assert
        assert result == "5:05"
