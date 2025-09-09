"""Cache settings for TiTiler following official documentation.

Based on: https://developmentseed.org/titiler/examples/code/tiler_with_cache/
"""

from pydantic_settings import BaseSettings
from typing import Optional


class CacheSettings(BaseSettings):
    """Cache settings following TiTiler official example."""

    endpoint: Optional[str] = None
    ttl: int = 86400  # 24 hours (increased from 1 hour)
    namespace: str = "salty-tiler"
    
    # Redis-specific settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Cache type selection
    cache_type: str = "memory"  # "memory" or "redis"

    class Config:
        """Model config."""
        env_file = ".env"
        env_prefix = "CACHE_"
        extra = "ignore"  # Ignore extra environment variables


cache_setting = CacheSettings()
