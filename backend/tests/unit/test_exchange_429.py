from __future__ import annotations

from unittest.mock import patch

from src.api.routers.sync import (
    _exchange_cooldowns,
    _exchange_on_cooldown,
    _set_exchange_cooldown,
    clear_exchange_cooldown,
)


class TestExchangeCooldown:
    def setup_method(self):
        # Clear cooldowns before each test
        _exchange_cooldowns.clear()

    def teardown_method(self):
        # Clear cooldowns after each test
        _exchange_cooldowns.clear()

    def test_exchange_on_cooldown_returns_false_when_no_cooldown_set(self):
        # Arrange
        user_id = 1

        # Act
        result = _exchange_on_cooldown(user_id)

        # Assert
        assert result is False

    def test_set_cooldown_then_on_cooldown_returns_true(self):
        # Arrange
        user_id = 1

        with patch("time.monotonic") as mock_monotonic:
            mock_monotonic.return_value = 1000.0

            # Act
            _set_exchange_cooldown(user_id)
            result = _exchange_on_cooldown(user_id)

        # Assert
        assert result is True

    def test_exchange_on_cooldown_returns_false_after_cooldown_expires(self):
        # Arrange
        user_id = 1

        with patch("time.monotonic") as mock_monotonic:
            mock_monotonic.return_value = 1000.0
            _set_exchange_cooldown(user_id)

            # Act — advance time by 30 minutes + 1 second
            mock_monotonic.return_value = 1000.0 + 1801
            result = _exchange_on_cooldown(user_id)

        # Assert
        assert result is False
        # User should be removed from cooldowns dict
        assert user_id not in _exchange_cooldowns

    def test_exchange_on_cooldown_returns_true_before_cooldown_expires(self):
        # Arrange
        user_id = 1

        with patch("time.monotonic") as mock_monotonic:
            mock_monotonic.return_value = 1000.0
            _set_exchange_cooldown(user_id)

            # Act — advance time by 29 minutes (before 30-minute cooldown expires)
            mock_monotonic.return_value = 1000.0 + 1740
            result = _exchange_on_cooldown(user_id)

        # Assert
        assert result is True

    def test_clear_exchange_cooldown_removes_active_cooldown(self):
        # Arrange
        user_id = 1
        _set_exchange_cooldown(user_id)
        assert _exchange_on_cooldown(user_id) is True

        # Act
        clear_exchange_cooldown(user_id)

        # Assert
        assert _exchange_on_cooldown(user_id) is False
        assert user_id not in _exchange_cooldowns

    def test_clear_exchange_cooldown_noop_when_no_cooldown(self):
        # Arrange — no cooldown set
        user_id = 99

        # Act — should not raise
        clear_exchange_cooldown(user_id)

        # Assert
        assert _exchange_on_cooldown(user_id) is False

    def test_multiple_users_cooldowns_are_independent(self):
        # Arrange
        user_1 = 1
        user_2 = 2

        with patch("time.monotonic") as mock_monotonic:
            mock_monotonic.return_value = 1000.0
            _set_exchange_cooldown(user_1)

            mock_monotonic.return_value = 2000.0
            _set_exchange_cooldown(user_2)

            # Act — advance time so user_1's cooldown expires but user_2's does not
            mock_monotonic.return_value = 1000.0 + 1801  # 30min + 1s from user_1's cooldown

            result_1 = _exchange_on_cooldown(user_1)
            result_2 = _exchange_on_cooldown(user_2)

        # Assert
        assert result_1 is False  # user_1's cooldown expired
        assert result_2 is True   # user_2's cooldown still active
