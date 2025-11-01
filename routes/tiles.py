from fastapi import APIRouter, HTTPException, Response, Query, Path
from services.tiler import render_tile

router = APIRouter()

@router.get("/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png")
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

    return Response(
        img,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-COG-URL": url,
            "X-Expression": expression,
            "X-Rescale": f"{min_val},{max_val}",
            "X-Tile-Coords": f"{z}/{x}/{y}"
        },
    ) 