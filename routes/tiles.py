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
    
    # Render tile using client-provided expression
    # TiTiler will automatically convert HTTP URLs to VSI paths when credentials are configured
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
        error_msg = str(e)
        # Check for authentication errors (403)
        if "403" in error_msg or "Forbidden" in error_msg:
            raise HTTPException(
                403, 
                f"Authentication failed. Check AWS credentials and S3 endpoint configuration. "
                f"Original error: {error_msg}"
            )
        # Check for other HTTP errors
        if "HTTP" in error_msg:
            status_code = 500
            if "404" in error_msg:
                status_code = 404
            raise HTTPException(status_code, f"Failed to access COG: {error_msg}")
        raise HTTPException(500, f"Tile rendering failed: {error_msg}")

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