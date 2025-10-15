"""Cache Plugin following TiTiler official documentation.

Based on: https://developmentseed.org/titiler/examples/code/tiler_with_cache/
"""

import asyncio
from typing import Any, Dict

import aiocache
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response
from fastapi.dependencies.utils import is_coroutine_callable

from cache_settings import cache_setting


class cached(aiocache.cached):
    """Custom Cached Decorator following TiTiler official example."""

    async def get_from_cache(self, key):
        try:
            value = await self.cache.get(key)
            if isinstance(value, Response):
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


def setup_cache():
    """Setup aiocache with in-memory backend."""
    config: Dict[str, Any] = {
        'cache': "aiocache.SimpleMemoryCache",
        'serializer': {
            'class': "aiocache.serializers.PickleSerializer"
        },
        'ttl': cache_setting.ttl,
        'namespace': cache_setting.namespace
    }

    aiocache.caches.set_config({"default": config})
    print(f"[CACHE] Initialized in-memory cache with TTL={cache_setting.ttl}s, namespace='{cache_setting.namespace}'")
