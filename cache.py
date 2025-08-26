"""Cache Plugin for TiTiler.

Provides in-memory caching using aiocache.SimpleMemoryCache.
Based on TiTiler's caching example but simplified for in-memory only.
"""

import asyncio
import os
from typing import Any, Dict

import aiocache
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response
from fastapi.dependencies.utils import is_coroutine_callable


class cached(aiocache.cached):
    """Custom Cached Decorator that supports both async and sync methods."""

    async def get_from_cache(self, key):
        try:
            value = await self.cache.get(key)
            if isinstance(value, Response):
                # Add cache hit header
                value.headers["X-Cache"] = "HIT"
            return value
        except Exception:
            aiocache.logger.exception(
                "Couldn't retrieve %s, unexpected error", key
            )

    async def decorator(
        self,
        f,
        *args,
        cache_read=True,
        cache_write=True,
        aiocache_wait_for_write=True,
        **kwargs,
    ):
        key = self.get_cache_key(f, args, kwargs)

        if cache_read:
            value = await self.get_from_cache(key)
            if value is not None:
                return value

        # Support for both async and sync methods
        if is_coroutine_callable(f):
            result = await f(*args, **kwargs)
        else:
            result = await run_in_threadpool(f, *args, **kwargs)

        # Add cache miss header for debugging
        if isinstance(result, Response):
            result.headers["X-Cache"] = "MISS"

        if cache_write:
            if aiocache_wait_for_write:
                await self.set_in_cache(key, result)
            else:
                asyncio.ensure_future(self.set_in_cache(key, result))

        return result


def setup_cache(ttl: int = None):
    """Setup aiocache with in-memory cache.
    
    Args:
        ttl: Time to live in seconds (default: from CACHE_TTL env or 1 hour)
    """
    # Use environment variable or provided TTL or default to 1 hour
    if ttl is None:
        ttl = int(os.getenv("CACHE_TTL", "3600"))
    config: Dict[str, Any] = {
        'cache': "aiocache.SimpleMemoryCache",
        'serializer': {
            'class': "aiocache.serializers.PickleSerializer"
        },
        'ttl': ttl,
    }
    
    aiocache.caches.set_config({"default": config})
    print(f"[CACHE] Initialized in-memory cache with TTL={ttl}s")
