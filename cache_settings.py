"""Cache settings for TiTiler following official documentation.

Based on: https://developmentseed.org/titiler/examples/code/tiler_with_cache/
"""

from pydantic_settings import BaseSettings


class CacheSettings(BaseSettings):
    """Cache settings for in-memory caching."""

    ttl: int = 86400  # 24 hours
    namespace: str = "salty-tiler"

    class Config:
        """Model config."""
        env_file = ".env"
        env_prefix = "CACHE_"
        extra = "ignore"  # Ignore extra environment variables


cache_setting = CacheSettings()
