from fastapi import APIRouter, HTTPException, Response, Query, Path
from services.tiler import render_tile
import requests
from dataclasses import dataclass

router = APIRouter()

@dataclass(frozen=True)
class DatasetStyle:
    """Dataset configuration for TiTiler native rendering."""
    expression: str
    rescale_min: float
    rescale_max: float
    default_colormap: str

# Dataset configurations using TiTiler native log expressions
DATASET_STYLES = {
    "chlorophyll": DatasetStyle(
        # Simple natural logarithm scaling: ln(value) - ln(0.01) / ln(8.0) - ln(0.01)
        expression="log(b1)",
        rescale_min=-4.6,    # ln(0.01) = -4.605
        rescale_max=2.08,    # ln(8.0) = 2.079
        default_colormap="chlorophyll"
    ),
    "water_clarity": DatasetStyle(
        # More aggressive piecewise: linear below 0.05, log above 0.05
        expression="(b1 <= 0.05) ? b1 : (0.05 + log10(b1/0.05))",
        rescale_min=0.02,    # Linear range: 0.02-0.05
        rescale_max=0.8,     # Log range: 0.05-6.0 → 0.05-0.8
        default_colormap="water_clarity"
    ),
    "sst": DatasetStyle(
        expression="b1",     # Linear scaling for temperature
        rescale_min=32.0,
        rescale_max=95.0,
        default_colormap="sst_high_contrast"
    ),
    "salinity": DatasetStyle(
        expression="b1",     # Linear scaling for salinity
        rescale_min=28.0,
        rescale_max=37.5,
        default_colormap="salinity"
    )
}

def validate_cog_url(url: str) -> bool:
    """Validate that the COG URL is accessible and is a valid TIFF file."""
    try:
        # Quick HEAD request to check if URL exists and is accessible
        response = requests.head(url, timeout=10)
        return response.status_code == 200 and 'tif' in url.lower()
    except:
        return False

@router.get("/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png")
def cog_tile_compatible(
    z: int = Path(...),
    x: int = Path(...),
    y: int = Path(...),
    url: str = Query(..., description="Full URL to COG file"),
    rescale: str = Query(..., description="Min,max range for rescaling (e.g., 32,86)"),
    colormap_name: str = Query(..., description="Colormap name (e.g., sst_high_contrast)"),
    resampling: str = Query("lanczos", description="Resampling method"),
):
    """
    TiTiler-compatible endpoint that matches the iOS app's URL format.
    Uses native TiTiler expressions for log scaling instead of transformations.
    
    Example: /cog/tiles/WebMercatorQuad/6/12/20.png?url=https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif&rescale=32,86&colormap_name=sst_high_contrast&resampling=lanczos
    """
    # Parse rescale parameter
    try:
        min_val, max_val = map(float, rescale.split(','))
    except ValueError:
        raise HTTPException(400, "rescale parameter must be in format 'min,max'")
    
    # Determine dataset style from colormap name
    dataset_style = None
    for style_name, style in DATASET_STYLES.items():
        if style.default_colormap == colormap_name:
            dataset_style = style
            break
    
    # Validate COG URL exists
    if not validate_cog_url(url):
        raise HTTPException(404, f"COG file not found or inaccessible: {url}")
    
    # Render tile using TiTiler's native expression support
    try:
        img = render_tile(
            path=url,
            z=z, x=x, y=y,
            min_value=min_val, max_value=max_val,
            colormap_name=colormap_name,
            colormap_bins=256,
            use_log_scale=False,  # No more custom log scaling
            dataset_type=None,
            expression=dataset_style.expression if dataset_style else "b1",
        )
    except Exception as e:
        raise HTTPException(404, f"Tile not available: {str(e)}")

    return Response(
        img,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-COG-URL": url,
        },
    ) 