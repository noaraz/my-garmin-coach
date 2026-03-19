from __future__ import annotations

from unittest.mock import patch


from src.core import cache


class TestCache:
    """Tests for in-memory TTL cache."""

    def test_get_returns_none_for_missing_key(self) -> None:
        # Arrange
        key = "nonexistent"

        # Act
        result = cache.get(key)

        # Assert
        assert result is None

    def test_set_and_get_returns_value(self) -> None:
        # Arrange
        key = "test-key"
        value = {"data": "test-value"}

        # Act
        cache.set(key, value)
        result = cache.get(key)

        # Assert
        assert result == value

    def test_get_returns_none_after_ttl_expires(self) -> None:
        # Arrange
        key = "expiring-key"
        value = "expires"
        ttl = 10

        with patch("src.core.cache.time") as mock_time:
            # Initial set at t=0
            mock_time.monotonic.return_value = 0.0
            cache.set(key, value, ttl=ttl)

            # Get before expiry at t=5
            mock_time.monotonic.return_value = 5.0
            assert cache.get(key) == value

            # Get after expiry at t=11
            mock_time.monotonic.return_value = 11.0
            result = cache.get(key)

        # Assert
        assert result is None

    def test_invalidate_removes_key(self) -> None:
        # Arrange
        key = "to-invalidate"
        cache.set(key, "value")

        # Act
        cache.invalidate(key)
        result = cache.get(key)

        # Assert
        assert result is None

    def test_invalidate_noop_for_missing_key(self) -> None:
        # Arrange
        key = "does-not-exist"

        # Act - should not raise
        cache.invalidate(key)

        # Assert - no exception
        assert cache.get(key) is None

    def test_invalidate_prefix_removes_matching_keys(self) -> None:
        # Arrange
        cache.set("user:1:profile", "data1")
        cache.set("user:1:settings", "data2")
        cache.set("user:2:profile", "data3")

        # Act
        cache.invalidate_prefix("user:1:")

        # Assert
        assert cache.get("user:1:profile") is None
        assert cache.get("user:1:settings") is None
        assert cache.get("user:2:profile") == "data3"

    def test_invalidate_prefix_keeps_non_matching(self) -> None:
        # Arrange
        cache.set("prefix:123", "match")
        cache.set("other:456", "keep")
        cache.set("prefix_wrong:789", "keep-also")

        # Act
        cache.invalidate_prefix("prefix:")

        # Assert
        assert cache.get("prefix:123") is None
        assert cache.get("other:456") == "keep"
        assert cache.get("prefix_wrong:789") == "keep-also"

    def test_clear_removes_all(self) -> None:
        # Arrange
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Act
        cache.clear()

        # Assert
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_set_overwrites_existing(self) -> None:
        # Arrange
        key = "overwrite-key"
        cache.set(key, "old-value")

        # Act
        cache.set(key, "new-value")
        result = cache.get(key)

        # Assert
        assert result == "new-value"

    def test_custom_ttl(self) -> None:
        # Arrange
        key = "short-ttl"
        value = "quick-expire"
        custom_ttl = 5

        with patch("src.core.cache.time") as mock_time:
            # Set at t=0 with custom TTL=5
            mock_time.monotonic.return_value = 0.0
            cache.set(key, value, ttl=custom_ttl)

            # Get at t=3 (before expiry)
            mock_time.monotonic.return_value = 3.0
            assert cache.get(key) == value

            # Get at t=6 (after expiry)
            mock_time.monotonic.return_value = 6.0
            result = cache.get(key)

        # Assert
        assert result is None
