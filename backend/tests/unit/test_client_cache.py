from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.garmin import client_cache


class TestClientCache:
    def setup_method(self):
        # Clear cache before each test
        client_cache.clear()

    def teardown_method(self):
        # Clear cache after each test
        client_cache.clear()

    def test_get_returns_none_when_cache_is_empty(self):
        # Arrange
        user_id = 1

        # Act
        result = client_cache.get(user_id)

        # Assert
        assert result is None

    def test_put_then_get_returns_the_adapter(self):
        # Arrange
        user_id = 1
        adapter = MagicMock()

        # Act
        client_cache.put(user_id, adapter)
        result = client_cache.get(user_id)

        # Assert
        assert result is adapter

    def test_invalidate_removes_entry(self):
        # Arrange
        user_id = 1
        adapter = MagicMock()
        client_cache.put(user_id, adapter)

        # Act
        client_cache.invalidate(user_id)
        result = client_cache.get(user_id)

        # Assert
        assert result is None

    def test_clear_removes_all_entries(self):
        # Arrange
        adapter_1 = MagicMock()
        adapter_2 = MagicMock()
        client_cache.put(1, adapter_1)
        client_cache.put(2, adapter_2)

        # Act
        client_cache.clear()

        # Assert
        assert client_cache.get(1) is None
        assert client_cache.get(2) is None

    def test_get_returns_none_after_ttl_expires(self):
        # Arrange
        user_id = 1
        adapter = MagicMock()
        # Mock time.monotonic to simulate time passing
        with patch("src.garmin.client_cache.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            client_cache.put(user_id, adapter)

            # Act — advance time by more than TTL (3600s + 1)
            mock_time.monotonic.return_value = 1000.0 + 3601.0
            result = client_cache.get(user_id)

        # Assert
        assert result is None

    def test_get_returns_adapter_before_ttl_expires(self):
        # Arrange
        user_id = 1
        adapter = MagicMock()
        # Mock time.monotonic to simulate time passing
        with patch("src.garmin.client_cache.time") as mock_time:
            mock_time.monotonic.return_value = 1000.0
            client_cache.put(user_id, adapter)

            # Act — advance time by less than TTL (3600s - 1)
            mock_time.monotonic.return_value = 1000.0 + 3599.0
            result = client_cache.get(user_id)

        # Assert
        assert result is adapter

    def test_put_overwrites_existing_entry(self):
        # Arrange
        user_id = 1
        adapter_old = MagicMock()
        adapter_new = MagicMock()
        client_cache.put(user_id, adapter_old)

        # Act
        client_cache.put(user_id, adapter_new)
        result = client_cache.get(user_id)

        # Assert
        assert result is adapter_new
        assert result is not adapter_old

    def test_invalidate_idempotent_when_user_not_in_cache(self):
        # Arrange
        user_id = 1

        # Act — invalidate a non-existent entry (should not raise)
        client_cache.invalidate(user_id)

        # Assert
        assert client_cache.get(user_id) is None
