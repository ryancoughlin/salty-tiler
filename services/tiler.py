from typing import Any, Dict
from titiler.core.factory import TilerFactory
from titiler.core.resources.enums import ImageType
from functools import lru_cache
import json

# TilerFactory instance with bilinear resampling
cog_tiler = TilerFactory(
    reader="rio_cog",
    default_reader_options={"resampling_method": "bilinear"}
)

# Simple set to track seen cache keys for hit/miss logging (dev only)
_seen_cache_keys = set()

def _serialize_colormap(colormap: Any) -> str:
    """Serialize colormap dict to a JSON string for hashing."""
    # Assume colormap is a dict[int, tuple[int, int, int, int]]
    # Sort keys for deterministic output
    return json.dumps(colormap, sort_keys=True)

@lru_cache(maxsize=2048)
def _render_tile_cached(
    path: str,
    z: int,
    x: int,
    y: int,
    min_value: float,
    max_value: float,
    colormap_serialized: str,
    colormap_bins: int = 256,
) -> bytes:
    colormap = json.loads(colormap_serialized)
    return cog_tiler.render(
        path=path,
        tile_format=ImageType.png,
        scale_range=[min_value, max_value],
        colormap=colormap,
        colormap_bins=colormap_bins,
        z=z, x=x, y=y
    )

def render_tile(
    path: str,
    z: int,
    x: int,
    y: int,
    min_value: float,
    max_value: float,
    colormap: Any,
    colormap_bins: int = 256,
) -> bytes:
    """
    Render a PNG tile from a COG using TiTiler with bilinear resampling and a custom colormap.
    Returns PNG bytes. Uses in-memory LRU cache for speed.
    Prints cache hit/miss for debugging.
    """
    colormap_serialized = _serialize_colormap(colormap)
    key = (path, z, x, y, min_value, max_value, colormap_serialized, colormap_bins)
    if key in _seen_cache_keys:
        print(f"[CACHE] HIT: {path} z={z} x={x} y={y} min={min_value} max={max_value}")
    else:
        print(f"[CACHE] MISS: {path} z={z} x={x} y={y} min={min_value} max={max_value}")
        _seen_cache_keys.add(key)
    return _render_tile_cached(*key) 