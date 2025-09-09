"""Cache Plugin following TiTiler official documentation.

Based on: https://developmentseed.org/titiler/examples/code/tiler_with_cache/
"""

import asyncio
import urllib
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
    """Setup aiocache with Redis or memory backend."""
    config: Dict[str, Any] = {
        'serializer': {
            'class': "aiocache.serializers.PickleSerializer"
        }
    }
    
    if cache_setting.ttl is not None:
        config["ttl"] = cache_setting.ttl
    
    if cache_setting.namespace:
        config["namespace"] = cache_setting.namespace

    # Configure cache backend based on settings
    if cache_setting.cache_type == "redis":
        config.update({
            'cache': "aiocache.RedisCache",
            'endpoint': cache_setting.redis_host,
            'port': cache_setting.redis_port,
            'db': cache_setting.redis_db,
        })
        if cache_setting.redis_password:
            config["password"] = cache_setting.redis_password
        backend_info = f"Redis at {cache_setting.redis_host}:{cache_setting.redis_port}/{cache_setting.redis_db}"
    else:
        config['cache'] = "aiocache.SimpleMemoryCache"
        backend_info = "in-memory"

    # Handle legacy endpoint configuration if provided
    if cache_setting.endpoint:
        url = urllib.parse.urlparse(cache_setting.endpoint)
        url_config = dict(urllib.parse.parse_qsl(url.query))
        config.update(url_config)

        cache_class = aiocache.Cache.get_scheme_class(url.scheme)
        config.update(cache_class.parse_uri_path(url.path))
        config["endpoint"] = url.hostname
        config["port"] = str(url.port)

        if url.password:
            config["password"] = url.password

        if cache_class == aiocache.Cache.REDIS:
            config["cache"] = "aiocache.RedisCache"
        elif cache_class == aiocache.Cache.MEMCACHED:
            config["cache"] = "aiocache.MemcachedCache"
        
        backend_info = f"endpoint {cache_setting.endpoint}"

    aiocache.caches.set_config({"default": config})
    print(f"[CACHE] Initialized {backend_info} cache with TTL={cache_setting.ttl}s, namespace='{cache_setting.namespace}'")
