"""
Redis client factory and rate-limiting helper.
Uses aioredis (bundled with redis-py >= 4.2) for async operations.
"""

import json
import time
from typing import Optional, Any
import redis.asyncio as aioredis
from app.config import get_settings

settings = get_settings()

# ── Singleton connection pool ──────────────────────────────────────────────────
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return the shared Redis client, creating it on first call."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis_client


async def close_redis() -> None:
    """Gracefully close the Redis connection pool (called on shutdown)."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


# ── Caching helpers ────────────────────────────────────────────────────────────

async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    """Serialize `value` to JSON and store it in Redis with a TTL."""
    client = await get_redis()
    await client.setex(key, ttl, json.dumps(value))


async def cache_get(key: str) -> Optional[Any]:
    """Retrieve and deserialize a cached value; returns None on miss."""
    client = await get_redis()
    raw = await client.get(key)
    return json.loads(raw) if raw is not None else None


async def cache_delete(key: str) -> None:
    """Remove a key from cache."""
    client = await get_redis()
    await client.delete(key)


# ── Rate-limiting helpers ──────────────────────────────────────────────────────

async def is_rate_limited(identifier: str) -> bool:
    """
    Sliding-window rate limiter.

    Returns True if the caller identified by `identifier` has exceeded
    RATE_LIMIT_REQUESTS within the last RATE_LIMIT_WINDOW_SECONDS.
    """
    client = await get_redis()
    key = f"rate_limit:{identifier}"
    now = time.time()
    window_start = now - settings.RATE_LIMIT_WINDOW_SECONDS

    pipe = client.pipeline()
    # Remove timestamps outside the current window
    pipe.zremrangebyscore(key, "-inf", window_start)
    # Count remaining requests in the window
    pipe.zcard(key)
    # Add current timestamp
    pipe.zadd(key, {str(now): now})
    # Reset TTL
    pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)
    results = await pipe.execute()

    current_count = results[1]
    return current_count >= settings.RATE_LIMIT_REQUESTS
