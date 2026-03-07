from __future__ import annotations

import pytest

from src.zone_engine.exceptions import ZoneValidationError
from src.zone_engine.hr_zones import HRZoneCalculator
from src.zone_engine.models import Zone, ZoneConfig, ZoneSet


class TestFromLthrCoggan:
    """test_from_lthr_coggan: LTHR=170, method=coggan → 5 zones with Coggan % boundaries"""

    def test_from_lthr_coggan_returns_five_zones(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=170.0, method="coggan")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()

        # Assert
        assert len(zone_set.zones) == 5

    def test_from_lthr_coggan_zone1_upper_boundary(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=170.0, method="coggan")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone1 = zone_set.get_zone(1)

        # Assert — Zone 1 upper: 68% of 170 = 115.6
        assert zone1.upper == pytest.approx(170.0 * 0.68, rel=1e-3)

    def test_from_lthr_coggan_zone2_boundaries(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=170.0, method="coggan")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone2 = zone_set.get_zone(2)

        # Assert — Zone 2: 68–83% of 170
        assert zone2.lower == pytest.approx(170.0 * 0.68, rel=1e-3)
        assert zone2.upper == pytest.approx(170.0 * 0.83, rel=1e-3)

    def test_from_lthr_coggan_zone3_boundaries(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=170.0, method="coggan")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone3 = zone_set.get_zone(3)

        # Assert — Zone 3: 83–94% of 170
        assert zone3.lower == pytest.approx(170.0 * 0.83, rel=1e-3)
        assert zone3.upper == pytest.approx(170.0 * 0.94, rel=1e-3)

    def test_from_lthr_coggan_zone4_boundaries(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=170.0, method="coggan")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone4 = zone_set.get_zone(4)

        # Assert — Zone 4: 94–105% of 170
        assert zone4.lower == pytest.approx(170.0 * 0.94, rel=1e-3)
        assert zone4.upper == pytest.approx(170.0 * 1.05, rel=1e-3)

    def test_from_lthr_coggan_zone5_boundaries(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=170.0, method="coggan")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone5 = zone_set.get_zone(5)

        # Assert — Zone 5 lower: 105% of 170; upper: 121% of 170
        assert zone5.lower == pytest.approx(170.0 * 1.05, rel=1e-3)
        assert zone5.upper == pytest.approx(170.0 * 1.21, rel=1e-3)


class TestFromMaxHr:
    """test_from_max_hr: maxHR=190, method=pct_max_hr → 5 zones as % of max HR"""

    def test_from_max_hr_returns_five_zones(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=190.0, method="pct_max_hr")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()

        # Assert
        assert len(zone_set.zones) == 5

    def test_from_max_hr_zone1_boundaries(self) -> None:
        # Arrange — max HR zones (% of max HR): Z1 50-60%, Z2 60-70%, Z3 70-80%, Z4 80-90%, Z5 90-100%
        config = ZoneConfig(threshold=190.0, method="pct_max_hr")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone1 = zone_set.get_zone(1)

        # Assert
        assert zone1.lower == pytest.approx(190.0 * 0.50, rel=1e-3)
        assert zone1.upper == pytest.approx(190.0 * 0.60, rel=1e-3)

    def test_from_max_hr_zone5_boundaries(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=190.0, method="pct_max_hr")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone5 = zone_set.get_zone(5)

        # Assert
        assert zone5.lower == pytest.approx(190.0 * 0.90, rel=1e-3)
        assert zone5.upper == pytest.approx(190.0 * 1.00, rel=1e-3)


class TestFromHrrKarvonen:
    """test_from_hrr_karvonen: maxHR=190, restHR=48, method=pct_hrr → 5 zones Karvonen"""

    def test_from_hrr_karvonen_returns_five_zones(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=190.0, resting_value=48.0, method="pct_hrr")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()

        # Assert
        assert len(zone_set.zones) == 5

    def test_from_hrr_karvonen_zone1_lower(self) -> None:
        # Arrange
        # HRR = 190 - 48 = 142; Zone1 lower = 48 + 0.50 * 142 = 119
        config = ZoneConfig(threshold=190.0, resting_value=48.0, method="pct_hrr")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone1 = zone_set.get_zone(1)

        # Assert
        hrr = 190.0 - 48.0
        assert zone1.lower == pytest.approx(48.0 + 0.50 * hrr, rel=1e-3)

    def test_from_hrr_karvonen_zone1_upper(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=190.0, resting_value=48.0, method="pct_hrr")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone1 = zone_set.get_zone(1)

        # Assert: zone1 upper = 48 + 0.60 * 142 = 133.2
        hrr = 190.0 - 48.0
        assert zone1.upper == pytest.approx(48.0 + 0.60 * hrr, rel=1e-3)

    def test_from_hrr_karvonen_zone5_upper(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=190.0, resting_value=48.0, method="pct_hrr")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone5 = zone_set.get_zone(5)

        # Assert: zone5 upper = 48 + 1.00 * 142 = 190
        hrr = 190.0 - 48.0
        assert zone5.upper == pytest.approx(48.0 + 1.00 * hrr, rel=1e-3)


class TestFromLthrFriel:
    """test_from_lthr_friel: LTHR=170, method=friel → 5 zones with Friel % boundaries"""

    def test_from_lthr_friel_returns_five_zones(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=170.0, method="friel")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()

        # Assert
        assert len(zone_set.zones) == 5

    def test_from_lthr_friel_zone1_upper_boundary(self) -> None:
        # Arrange — Friel Z1 upper: 81% of LTHR (differs from Coggan 68%)
        config = ZoneConfig(threshold=170.0, method="friel")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone1 = zone_set.get_zone(1)

        # Assert
        assert zone1.upper == pytest.approx(170.0 * 0.81, rel=1e-3)

    def test_from_lthr_friel_zone5_boundaries(self) -> None:
        # Arrange — Friel Z5: 100–110% of LTHR
        config = ZoneConfig(threshold=170.0, method="friel")
        calc = HRZoneCalculator(config)

        # Act
        zone_set = calc.calculate()
        zone5 = zone_set.get_zone(5)

        # Assert
        assert zone5.lower == pytest.approx(170.0 * 1.00, rel=1e-3)
        assert zone5.upper == pytest.approx(170.0 * 1.10, rel=1e-3)

    def test_from_lthr_friel_differs_from_coggan(self) -> None:
        # Arrange — Friel and Coggan should produce different zone boundaries
        coggan = HRZoneCalculator(ZoneConfig(threshold=170.0, method="coggan")).calculate()
        friel = HRZoneCalculator(ZoneConfig(threshold=170.0, method="friel")).calculate()

        # Act & Assert — Zone 5 upper: Coggan 121% vs Friel 110%
        assert friel.get_zone(5).upper != coggan.get_zone(5).upper


class TestCustomHrZones:
    """test_custom: explicit bpm boundaries → stored as-is"""

    def test_custom_zones_stored_as_is(self) -> None:
        # Arrange
        custom_zones = [
            Zone(zone_number=1, name="Z1", lower=100.0, upper=120.0, pct_lower=0.0, pct_upper=0.0),
            Zone(zone_number=2, name="Z2", lower=120.0, upper=140.0, pct_lower=0.0, pct_upper=0.0),
            Zone(zone_number=3, name="Z3", lower=140.0, upper=155.0, pct_lower=0.0, pct_upper=0.0),
            Zone(zone_number=4, name="Z4", lower=155.0, upper=165.0, pct_lower=0.0, pct_upper=0.0),
            Zone(zone_number=5, name="Z5", lower=165.0, upper=185.0, pct_lower=0.0, pct_upper=0.0),
        ]
        config = ZoneConfig(threshold=0.0, method="custom")
        zone_set = ZoneSet(config=config, zones=custom_zones)

        # Act & Assert — exact values stored
        assert zone_set.get_zone(1).lower == 100.0
        assert zone_set.get_zone(1).upper == 120.0
        assert zone_set.get_zone(3).lower == 140.0
        assert zone_set.get_zone(5).upper == 185.0


class TestRecalculateOnLthrChange:
    """test_recalculate_on_lthr_change: LTHR 170→175 → all 5 zones shift"""

    def test_recalculate_zones_shift_on_lthr_increase(self) -> None:
        # Arrange
        config_170 = ZoneConfig(threshold=170.0, method="coggan")
        config_175 = ZoneConfig(threshold=175.0, method="coggan")
        calc_170 = HRZoneCalculator(config_170)
        calc_175 = HRZoneCalculator(config_175)

        # Act
        zones_170 = calc_170.calculate()
        zones_175 = calc_175.calculate()

        # Assert — all zone upper boundaries shift up (zone 1 lower is 0 for both)
        # Start from zone 2 lower since zone 1 lower = 0 * LTHR = 0 for any LTHR
        for i in range(1, 6):
            assert zones_175.get_zone(i).upper > zones_170.get_zone(i).upper
        # Zones 2-5 lower boundaries also shift up
        for i in range(2, 6):
            assert zones_175.get_zone(i).lower > zones_170.get_zone(i).lower


class TestLookupByNumber:
    """test_lookup_by_number: zone 3 returned correctly"""

    def test_lookup_zone3_returns_correct_zone(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=170.0, method="coggan")
        calc = HRZoneCalculator(config)
        zone_set = calc.calculate()

        # Act
        zone3 = zone_set.get_zone(3)

        # Assert
        assert zone3.zone_number == 3
        assert zone3.lower == pytest.approx(170.0 * 0.83, rel=1e-3)


class TestValidationErrors:
    """Validation error tests"""

    def test_rejects_zero_lthr(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ZoneValidationError):
            config = ZoneConfig(threshold=0.0, method="coggan")
            calc = HRZoneCalculator(config)
            calc.calculate()

    def test_rejects_negative_lthr(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(ZoneValidationError):
            config = ZoneConfig(threshold=-5.0, method="coggan")
            calc = HRZoneCalculator(config)
            calc.calculate()

    def test_rejects_zero_resting_hr_in_karvonen(self) -> None:
        # Arrange — resting_hr defaults to 0.0; Karvonen with 0 is degenerate
        config = ZoneConfig(threshold=190.0, resting_value=0.0, method="pct_hrr")
        calc = HRZoneCalculator(config)

        # Act & Assert
        with pytest.raises(ZoneValidationError):
            calc.calculate()

    def test_rejects_out_of_range_zone_number(self) -> None:
        # Arrange
        config = ZoneConfig(threshold=170.0, method="coggan")
        calc = HRZoneCalculator(config)
        zone_set = calc.calculate()

        # Act & Assert
        with pytest.raises(ZoneValidationError):
            zone_set.get_zone(6)
