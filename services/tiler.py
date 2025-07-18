from typing import Any, Dict, Optional
from titiler.core.factory import TilerFactory
from titiler.core.resources.enums import ImageType
from functools import lru_cache
import json
import os
import numpy as np

# TilerFactory instance with bilinear resampling
cog_tiler = TilerFactory()

# Simple set to track seen cache keys for hit/miss logging (dev only)
_seen_cache_keys = set()

def _symlog_transform(value: float, linthresh: float = 0.3, base: float = 2.0) -> float:
    """
    Apply symmetric log transformation matching the visualizer's SymLogNorm.
    
    This mimics matplotlib's SymLogNorm transformation:
    - Linear scaling below linthresh
    - Logarithmic scaling above linthresh
    
    Args:
        value: Input value to transform
        linthresh: Linear threshold (0.3 for chlorophyll)
        base: Logarithmic base (2 for chlorophyll)
    """
    if value <= linthresh:
        return value / linthresh
    else:
        return 1.0 + np.log(value / linthresh) / np.log(base)

def _apply_chlorophyll_scaling(min_val: float, max_val: float) -> tuple[float, float]:
    """
    Apply the same logarithmic scaling used in the visualizer for chlorophyll data.
    
    This transforms the min/max values to match the SymLogNorm scaling:
    vmin=0.01, vmax=20.0, linthresh=0.3, base=2
    """
    # Apply symlog transformation to both min and max
    transformed_min = _symlog_transform(min_val, linthresh=0.3, base=2.0)
    transformed_max = _symlog_transform(max_val, linthresh=0.3, base=2.0)
    
    return transformed_min, transformed_max

def _serialize_colormap(colormap: Any) -> str:
    """Serialize colormap dict to a JSON string for hashing."""
    # Assume colormap is a dict[int, tuple[int, int, int, int]]
    # Sort keys for deterministic output
    return json.dumps(colormap, sort_keys=True) if colormap else "null"

@lru_cache(maxsize=int(os.getenv("TILE_CACHE_SIZE", "2048")))
def _render_tile_cached(
    path: str,
    z: int,
    x: int,
    y: int,
    min_value: float,
    max_value: float,
    colormap_serialized: str,
    colormap_name: Optional[str] = None,
    colormap_bins: int = 256,
) -> bytes:
    kwargs = {
        "path": path,
        "tile_format": ImageType.png,
        "scale_range": [min_value, max_value],
        "colormap_bins": colormap_bins,
        "resampling_method": "bilinear",
        "z": z, "x": x, "y": y
    }
    
    # Either use a named colormap or a custom colormap dictionary
    if colormap_name:
        kwargs["colormap_name"] = colormap_name
    elif colormap_serialized != "null":
        kwargs["colormap"] = json.loads(colormap_serialized)
        
    return cog_tiler.render(**kwargs)

def render_tile(
    path: str,
    z: int,
    x: int,
    y: int,
    min_value: float,
    max_value: float,
    colormap: Any = None,
    colormap_name: Optional[str] = None,
    colormap_bins: int = 256,
    use_log_scale: bool = False,
) -> bytes:
    """
    Render a PNG tile from a COG using TiTiler with bilinear resampling and a colormap.
    Returns PNG bytes. Uses in-memory LRU cache for speed.
    Supports both local paths and external URLs.
    
    Args:
        path: Path or URL to the COG file
        z, x, y: Tile coordinates
        min_value, max_value: Scale range for colormap
        colormap: Custom colormap dict
        colormap_name: Named colormap registered in app
        colormap_bins: Number of colormap bins
        use_log_scale: Apply logarithmic scaling for chlorophyll data
    """
    # Apply logarithmic scaling for chlorophyll data to match visualizer
    if use_log_scale:
        min_value, max_value = _apply_chlorophyll_scaling(min_value, max_value)
    
    colormap_serialized = _serialize_colormap(colormap)
    key = (path, z, x, y, min_value, max_value, colormap_serialized, colormap_name, colormap_bins)
    
    # Log cache status
    cache_status = "HIT" if key in _seen_cache_keys else "MISS"
    url_type = "URL" if path.startswith("http") else "LOCAL"
    scale_type = "LOG" if use_log_scale else "LINEAR"
    print(f"[CACHE] {cache_status}: {url_type} {path} z={z} x={x} y={y} min={min_value} max={max_value} scale={scale_type}")
    
    if key not in _seen_cache_keys:
        _seen_cache_keys.add(key)
    
    return _render_tile_cached(*key) 