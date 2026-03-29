from __future__ import annotations

import time

from src.garmin.adapter import GarminAdapter

# Cache entry: (adapter, timestamp)
_cache: dict[int, tuple[GarminAdapter, float]] = {}
_TTL_SECONDS = 3600  # 1 hour


def get(user_id: int) -> GarminAdapter | None:
    """Get cached GarminAdapter for user if still valid."""
    entry = _cache.get(user_id)
    if entry is None:
        return None
    adapter, ts = entry
    if time.monotonic() - ts > _TTL_SECONDS:
        del _cache[user_id]
        return None
    return adapter


def put(user_id: int, adapter: GarminAdapter) -> None:
    """Store a GarminAdapter in the cache."""
    _cache[user_id] = (adapter, time.monotonic())


def invalidate(user_id: int) -> None:
    """Remove a user's adapter from the cache."""
    _cache.pop(user_id, None)


def clear() -> None:
    """Clear the entire cache (e.g., on config reload)."""
    _cache.clear()
