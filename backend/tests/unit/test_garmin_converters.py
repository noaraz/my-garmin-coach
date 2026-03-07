from __future__ import annotations

import pytest

from src.garmin.converters import pace_to_speed, speed_to_pace, step_type_to_id
from src.garmin.exceptions import FormatterError


class TestPaceToSpeed:
    def test_pace_to_speed_300_secperkm_returns_3333_mps(self) -> None:
        # Arrange
        pace_seconds = 300  # 5:00/km

        # Act
        result = pace_to_speed(pace_seconds)

        # Assert
        assert abs(result - 3.333) < 0.001

    def test_pace_to_speed_600_secperkm_returns_1667_mps(self) -> None:
        # Arrange
        pace_seconds = 600  # 10:00/km

        # Act
        result = pace_to_speed(pace_seconds)

        # Assert
        assert abs(result - 1.667) < 0.001


class TestSpeedToPace:
    def test_speed_to_pace_3333_mps_returns_300_secperkm(self) -> None:
        # Arrange
        speed_mps = 3.333

        # Act
        result = speed_to_pace(speed_mps)

        # Assert
        assert abs(result - 300) < 1

    def test_speed_to_pace_1667_mps_returns_600_secperkm(self) -> None:
        # Arrange
        speed_mps = 1.667

        # Act
        result = speed_to_pace(speed_mps)

        # Assert
        assert abs(result - 600) < 1


class TestRoundtrip:
    @pytest.mark.parametrize("pace", [240, 300, 360, 420, 480, 540])
    def test_roundtrip_pace_to_speed_and_back_within_1s(self, pace: int) -> None:
        # Arrange & Act
        speed = pace_to_speed(pace)
        recovered_pace = speed_to_pace(speed)

        # Assert
        assert abs(recovered_pace - pace) < 1


class TestStepTypeToId:
    def test_step_type_to_id_warmup_returns_1(self) -> None:
        # Arrange & Act
        result = step_type_to_id("warmup")

        # Assert
        assert result == 1

    def test_step_type_to_id_cooldown_returns_2(self) -> None:
        # Arrange & Act
        result = step_type_to_id("cooldown")

        # Assert
        assert result == 2

    def test_step_type_to_id_active_returns_3(self) -> None:
        # Active maps to interval (id=3) in Garmin
        # Arrange & Act
        result = step_type_to_id("active")

        # Assert
        assert result == 3

    def test_step_type_to_id_recovery_returns_4(self) -> None:
        # Arrange & Act
        result = step_type_to_id("recovery")

        # Assert
        assert result == 4

    def test_step_type_to_id_rest_returns_5(self) -> None:
        # Arrange & Act
        result = step_type_to_id("rest")

        # Assert
        assert result == 5

    def test_step_type_to_id_repeat_returns_6(self) -> None:
        # Arrange & Act
        result = step_type_to_id("repeat")

        # Assert
        assert result == 6


class TestUnknownTypeRaises:
    def test_unknown_type_raises_formatter_error(self) -> None:
        # Arrange
        invalid_type = "invalid"

        # Act & Assert
        with pytest.raises(FormatterError):
            step_type_to_id(invalid_type)

    def test_empty_string_raises_formatter_error(self) -> None:
        # Arrange & Act & Assert
        with pytest.raises(FormatterError):
            step_type_to_id("")
