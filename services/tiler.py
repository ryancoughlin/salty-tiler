from typing import Any, Dict, Optional
from titiler.core.factory import TilerFactory
from titiler.mosaic.factory import MosaicTilerFactory
from titiler.core.resources.enums import ImageType
from functools import lru_cache
import json
import os
import numpy as np
import time
from collections import defaultdict

# TilerFactory instance with bilinear resampling
cog_tiler = TilerFactory()

# MosaicTilerFactory instance for MosaicJSON support
mosaic_tiler = MosaicTilerFactory()

# Simple set to track seen cache keys for hit/miss logging (dev only)
_seen_cache_keys = set()

# Request throttling for concurrent COG access
_last_request_time = defaultdict(float)
_min_request_interval = 0.05  # 50ms between requests to same COG (reduced from 100ms)

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

def _throttle_cog_request(path: str):
    """
    Light throttling to prevent overwhelming GDAL HTTP driver during timeline scrubbing.
    """
    if path.startswith(('http://', 'https://')):
        current_time = time.time()
        last_time = _last_request_time[path]
        
        if current_time - last_time < _min_request_interval:
            sleep_time = _min_request_interval - (current_time - last_time)
            time.sleep(sleep_time)
        
        _last_request_time[path] = time.time()

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
    expression: str = "b1",
) -> bytes:
    """
    Render a PNG tile from a COG using TiTiler with bilinear resampling and a colormap.
    Returns PNG bytes. Uses small LRU cache for performance.
    Supports both local paths and external URLs.
    
    Args:
        path: Path or URL to the COG file
        z, x, y: Tile coordinates
        min_value, max_value: Scale range for colormap
        colormap_serialized: Serialized colormap for cache key
        colormap_name: Named colormap registered in app
        colormap_bins: Number of colormap bins
        expression: TiTiler expression for data transformation
    """
    
    kwargs = {
        "path": path,
        "tile_format": ImageType.png,
        "scale_range": [min_value, max_value],
        "colormap_bins": colormap_bins,
        "resampling_method": "bilinear",
        "z": z, "x": x, "y": y
    }
    
    # Use named colormap
    if colormap_name:
        kwargs["colormap_name"] = colormap_name
        
    # Add expression if provided
    if expression != "b1":
        kwargs["expression"] = expression
        
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
    dataset_type: Optional[str] = None,
    expression: str = "b1",
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
        use_log_scale: Deprecated - use expression parameter instead
        dataset_type: Deprecated - use expression parameter instead
        expression: TiTiler expression for data transformation (e.g., "log10(b1+1e-6)")
    """
    # No more custom log scaling - use TiTiler's native expression support
    
    _throttle_cog_request(path)
    colormap_serialized = _serialize_colormap(colormap)
    key = (path, z, x, y, min_value, max_value, colormap_serialized, colormap_name, colormap_bins, expression)
    cache_status = "HIT" if key in _seen_cache_keys else "MISS"
    url_type = "URL" if path.startswith("http") else "LOCAL"
    scale_type = "EXPR" if expression != "b1" else "LINEAR"
    print(f"[CACHE] {cache_status}: {url_type} {path} z={z} x={x} y={y} min={min_value} max={max_value} scale={scale_type} expr={expression}")
    if key not in _seen_cache_keys:
        _seen_cache_keys.add(key)
    return _render_tile_cached(path, z, x, y, min_value, max_value, colormap_serialized, colormap_name, colormap_bins, expression) 

@lru_cache(maxsize=int(os.getenv("MOSAIC_CACHE_SIZE", "512")))
def _render_mosaic_tile_cached(
    mosaic_url: str,
    z: int,
    x: int,
    y: int,
    min_value: float,
    max_value: float,
    colormap_name: Optional[str] = None,
    colormap_bins: int = 256,
    resampling: str = "bilinear",
) -> bytes:
    """
    Render a PNG tile from a MosaicJSON using TiTiler.
    Returns PNG bytes. Uses LRU cache for performance.
    
    Args:
        mosaic_url: URL to MosaicJSON file
        z, x, y: Tile coordinates
        min_value, max_value: Scale range for colormap
        colormap_name: Named colormap registered in app
        colormap_bins: Number of colormap bins
        resampling: Resampling method
    """
    
    kwargs = {
        "path": mosaic_url,
        "tile_format": ImageType.png,
        "scale_range": [min_value, max_value],
        "colormap_bins": colormap_bins,
        "resampling_method": resampling,
        "z": z, "x": x, "y": y
    }
    
    # Use named colormap
    if colormap_name:
        kwargs["colormap_name"] = colormap_name
        
    return mosaic_tiler.render(**kwargs)

def render_mosaic_tile(
    mosaic_url: str,
    z: int,
    x: int,
    y: int,
    min_value: float,
    max_value: float,
    colormap_name: Optional[str] = None,
    colormap_bins: int = 256,
    resampling: str = "bilinear",
) -> bytes:
    """
    Render a PNG tile from a MosaicJSON using TiTiler.
    Returns PNG bytes. Uses in-memory LRU cache for speed.
    
    Args:
        mosaic_url: URL to MosaicJSON file
        z, x, y: Tile coordinates
        min_value, max_value: Scale range for colormap
        colormap_name: Named colormap registered in app
        colormap_bins: Number of colormap bins
        resampling: Resampling method
    """
    print(f"[MOSAIC] Rendering tile z={z} x={x} y={y} from {mosaic_url} range={min_value},{max_value}")
    return _render_mosaic_tile_cached(mosaic_url, z, x, y, min_value, max_value, colormap_name, colormap_bins, resampling)

@lru_cache(maxsize=int(os.getenv("POINT_CACHE_SIZE", "1024")))
def _query_mosaic_point_cached(
    mosaic_url: str,
    lon: float,
    lat: float,
) -> Dict[str, Any]:
    """
    Query a point value from a MosaicJSON using TiTiler.
    Returns point data with values.
    
    Args:
        mosaic_url: URL to MosaicJSON file
        lon, lat: Longitude and latitude coordinates
    """
    
    kwargs = {
        "path": mosaic_url,
        "coordinates": [lon, lat],
    }
        
    return mosaic_tiler.point(**kwargs)

def query_mosaic_point(
    mosaic_url: str,
    lon: float,
    lat: float,
) -> Dict[str, Any]:
    """
    Query a point value from a MosaicJSON using TiTiler.
    Returns point data with values.
    
    Args:
        mosaic_url: URL to MosaicJSON file
        lon, lat: Longitude and latitude coordinates
    """
    print(f"[MOSAIC] Querying point {lon},{lat} from {mosaic_url}")
    return _query_mosaic_point_cached(mosaic_url, lon, lat) 
