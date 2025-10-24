from fastapi import APIRouter, HTTPException, Response, Query, Path
from services.tiler import render_tile
from cache_plugin import cached
import hashlib
from typing import Optional

router = APIRouter()

def generate_tile_cache_key(url: str, z: int, x: int, y: int, rescale: str, colormap_name: str, expression: str) -> str:
    """
    Generate optimized cache key for tile requests.
    
    Format: tile:{url_hash}:{z}:{x}:{y}:{rescale_hash}:{colormap}:{expr_hash}
    This keeps keys short while ensuring uniqueness.
    """
    # Hash the URL to keep keys manageable
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    
    # Hash rescale values for shorter keys
    rescale_hash = hashlib.md5(rescale.encode()).hexdigest()[:6]
    
    # Hash expression if it's not the default
    expr_hash = hashlib.md5(expression.encode()).hexdigest()[:6] if expression != "b1" else "default"
    
    return f"tile:{url_hash}:{z}:{x}:{y}:{rescale_hash}:{colormap_name}:{expr_hash}"

@router.get("/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png")
@cached(alias="default")
def cog_tile_compatible(
    z: int = Path(...),
    x: int = Path(...),
    y: int = Path(...),
    url: str = Query(..., description="Full URL to COG file"),
    rescale: str = Query(..., description="Min,max range for rescaling (e.g., 32,86)"),
    colormap_name: str = Query(..., description="Colormap name (e.g., sst_high_contrast)"),
    resampling: str = Query("lanczos", description="Resampling method"),
    expression: str = Query("b1", description="TiTiler expression (e.g., log10(b1+1e-6))"),
):
    """
    Simple TiTiler-compatible endpoint that passes through all parameters.
    
    Client handles all expressions and scaling natively.
    
    Example: /cog/tiles/WebMercatorQuad/6/12/20.png?url=https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif&rescale=0.01,8.0&colormap_name=chlorophyll&expression=log10(b1+1e-6)
    """
    # Parse rescale parameter
    try:
        min_val, max_val = map(float, rescale.split(','))
    except ValueError:
        raise HTTPException(400, "rescale parameter must be in format 'min,max'")
    
    # Render tile using client-provided expression (TiTiler/GDAL will handle COG access errors)
    try:
        img = render_tile(
            path=url,
            z=z, x=x, y=y,
            min_value=min_val, max_value=max_val,
            colormap_name=colormap_name,
            colormap_bins=256,
            expression=expression,
        )
    except Exception as e:
        raise HTTPException(404, f"Tile not available: {str(e)}")

    # Generate cache key for debugging
    cache_key = generate_tile_cache_key(url, z, x, y, rescale, colormap_name, expression)
    
    return Response(
        img,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-COG-URL": url,
            "X-Expression": expression,
            "X-Rescale": f"{min_val},{max_val}",
            "X-Cache-Key": cache_key,
            "X-Tile-Coords": f"{z}/{x}/{y}"
        },
    ) 