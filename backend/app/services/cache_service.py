"""
Redis cache service for recommendation and profile caching.

Cache strategy:
- User profiles: cached for 5 min, invalidated on new events
- Ad recommendations: cached for 5 min, invalidated on click/skip
- Platform analytics: cached for 2 min, time-based expiry
- Trending content: cached for 5 min, time-based expiry
"""

import json
import logging
from typing import Optional, Any

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    """Get or create Redis connection. Returns None if Redis is unavailable."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _redis_client.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.warning(f"Redis unavailable (caching disabled): {e}")
            _redis_client = None
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    """Get a cached value. Returns None on miss or if Redis is unavailable."""
    client = await get_redis()
    if not client:
        return None
    try:
        value = await client.get(key)
        if value:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(value)
        logger.debug(f"Cache MISS: {key}")
        return None
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 300):
    """Set a cached value with TTL."""
    client = await get_redis()
    if not client:
        return
    try:
        await client.setex(key, ttl_seconds, json.dumps(value, default=str))
        logger.debug(f"Cache SET: {key} (TTL: {ttl_seconds}s)")
    except Exception as e:
        logger.warning(f"Cache set error: {e}")


async def cache_invalidate(pattern: str):
    """Invalidate cache keys matching a pattern."""
    client = await get_redis()
    if not client:
        return
    try:
        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await client.delete(*keys)
            logger.info(f"Cache invalidated: {pattern} ({len(keys)} keys)")
    except Exception as e:
        logger.warning(f"Cache invalidate error: {e}")


async def cache_invalidate_user(user_id: int):
    """Invalidate all cached data for a specific user."""
    await cache_invalidate(f"user:profile:{user_id}")
    await cache_invalidate(f"recs:ads:{user_id}")
    await cache_invalidate(f"recs:content:{user_id}")
