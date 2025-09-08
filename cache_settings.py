"""Cache settings for TiTiler following official documentation.

Based on: https://developmentseed.org/titiler/examples/code/tiler_with_cache/
"""

from pydantic_settings import BaseSettings
from typing import Optional


class CacheSettings(BaseSettings):
    """Cache settings following TiTiler official example."""

    endpoint: Optional[str] = None
    ttl: int = 86400  # 24 hours (increased from 1 hour)
    namespace: str = ""

    class Config:
        """Model config."""
        env_file = ".env"
        env_prefix = "CACHE_"


cache_setting = CacheSettings()
