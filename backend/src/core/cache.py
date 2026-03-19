"""Simple in-memory TTL cache for reducing DB queries."""

from __future__ import annotations

import time
from typing import Any

_store: dict[str, tuple[float, Any]] = {}

DEFAULT_TTL = 60  # seconds


def get(key: str) -> Any | None:
    """Get a cached value by key.

    Returns None if the key doesn't exist or has expired.
    Expired entries are removed from the cache.
    """
    entry = _store.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() > expires_at:
        del _store[key]
        return None
    return value


def set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    """Set a cached value with TTL in seconds.

    Args:
        key: Cache key
        value: Value to cache (any type)
        ttl: Time to live in seconds (default: 60)
    """
    _store[key] = (time.monotonic() + ttl, value)


def invalidate(key: str) -> None:
    """Remove a single key from the cache.

    Does nothing if the key doesn't exist.
    """
    _store.pop(key, None)


def invalidate_prefix(prefix: str) -> None:
    """Remove all keys starting with the given prefix.

    Useful for bulk invalidation, e.g., invalidate_prefix("user:123:")
    removes all cached data for user 123.
    """
    keys_to_remove = [k for k in _store if k.startswith(prefix)]
    for k in keys_to_remove:
        del _store[k]


def clear() -> None:
    """Remove all entries from the cache."""
    _store.clear()
