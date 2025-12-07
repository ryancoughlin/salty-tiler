from typing import Any, Optional
from titiler.core.factory import TilerFactory
from titiler.core.resources.enums import ImageType

# Import colormap registration
from services.colors import register_colormaps
# Import storage utilities for S3 path conversion
from services.storage import get_cog_path

# Register colormaps and get the dependency
ColorMapParams, cmap = register_colormaps()

# TilerFactory instance with bilinear resampling and custom colormaps
cog_tiler = TilerFactory(colormap_dependency=ColorMapParams)

def _render_tile(
    path: str,
    z: int,
    x: int,
    y: int,
    min_value: float,
    max_value: float,
    colormap_name: Optional[str] = None,
    colormap_bins: int = 256,
    expression: str = "b1",
    resampling_method: str = "bilinear",
) -> bytes:
    """
    Render a PNG tile from a COG using TiTiler with bilinear resampling and a colormap.
    Returns PNG bytes. Cloudflare handles caching at the edge.
    Supports both local paths and external URLs.
    
    Automatically converts HTTP URLs to VSI paths when S3 credentials are configured,
    enabling authenticated access to S3-compatible storage (DigitalOcean Spaces, AWS S3, etc.).
    
    Args:
        path: Path or URL to the COG file
        z, x, y: Tile coordinates
        min_value, max_value: Scale range for colormap
        colormap_name: Named colormap registered in app
        colormap_bins: Number of colormap bins
        expression: TiTiler expression for data transformation
    """
    # Convert HTTP URLs to VSI paths when credentials are available
    # This enables authenticated access to S3-compatible storage
    cog_path = get_cog_path(path, prefer_vsi=True)
    
    kwargs = {
        "path": cog_path,
        "tile_format": ImageType.png,
        "scale_range": [min_value, max_value],
        "colormap_bins": colormap_bins,
        "resampling_method": resampling_method,
        "z": z, "x": x, "y": y
    }
    
    # Use named colormap
    if colormap_name:
        kwargs["colormap_name"] = colormap_name
        
    # Add expression if provided
    if expression != "b1":
        kwargs["expression"] = expression

    # Render tile with TiTiler
    content = cog_tiler.render(**kwargs)

    # Return PNG directly (smoothing handled by algorithms if requested)
    return content

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
    resampling_method: str = "bilinear",
) -> bytes:
    """
    Render a PNG tile from a COG using TiTiler with bilinear resampling and a colormap.
    Returns PNG bytes. Cloudflare handles caching at the edge.
    Supports both local paths and external URLs.
    
    Args:
        path: Path or URL to the COG file
        z, x, y: Tile coordinates
        min_value, max_value: Scale range for colormap
        colormap: Custom colormap dict (deprecated, use colormap_name)
        colormap_name: Named colormap registered in app
        colormap_bins: Number of colormap bins
        use_log_scale: Deprecated - use expression parameter instead
        dataset_type: Deprecated - use expression parameter instead
        expression: TiTiler expression for data transformation (e.g., "log10(b1+1e-6)")
    """
    return _render_tile(path, z, x, y, min_value, max_value, colormap_name, colormap_bins, expression, resampling_method) 

