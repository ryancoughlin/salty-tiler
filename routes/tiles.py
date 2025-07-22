from fastapi import APIRouter, HTTPException, Response, Query, Path
from services.tiler import render_tile
import requests
from dataclasses import dataclass
import math
from typing import Optional

router = APIRouter()

@dataclass(frozen=True)
class DatasetConfig:
    """Dataset configuration for smart log scaling."""
    use_log: bool
    default_colormap: str

# Dataset configurations - server decides log vs linear
DATASETS = {
    "chlorophyll": DatasetConfig(
        use_log=True,
        default_colormap="chlorophyll"
    ),
    "water_clarity": DatasetConfig(
        use_log=True, 
        default_colormap="water_clarity"
    ),
    "sst": DatasetConfig(
        use_log=False,
        default_colormap="sst_high_contrast"
    ),
    "salinity": DatasetConfig(
        use_log=False,
        default_colormap="salinity"
    )
}

def convert_to_log_domain(min_val: float, max_val: float) -> tuple[float, float]:
    """Convert linear domain min/max to log10 domain."""
    # Add small offset to avoid log(0)
    offset = 1e-6
    return (
        math.log10(min_val + offset),
        math.log10(max_val + offset)
    )

def detect_dataset_from_colormap(colormap_name: str) -> Optional[str]:
    """Detect dataset type from colormap name."""
    for dataset, config in DATASETS.items():
        if config.default_colormap == colormap_name:
            return dataset
    return None

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
    Smart TiTiler-compatible endpoint that handles log scaling automatically.
    
    Client sends linear domain values, server converts to log domain if needed.
    
    Example: /cog/tiles/WebMercatorQuad/6/12/20.png?url=https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif&rescale=0.01,8.0&colormap_name=chlorophyll&resampling=lanczos
    """
    # Parse rescale parameter
    try:
        min_val, max_val = map(float, rescale.split(','))
    except ValueError:
        raise HTTPException(400, "rescale parameter must be in format 'min,max'")
    
    # Detect dataset from colormap name
    dataset = detect_dataset_from_colormap(colormap_name)
    
    # Determine expression and rescale based on dataset type
    if dataset and DATASETS[dataset].use_log:
        # Use log10 scaling for log datasets
        expression = "log10(b1+1e-6)"
        rescale_lo, rescale_hi = convert_to_log_domain(min_val, max_val)
        print(f"[LOG] Converting {dataset}: linear {min_val},{max_val} → log {rescale_lo:.3f},{rescale_hi:.3f}")
    else:
        # Use linear scaling for linear datasets
        expression = "b1"
        rescale_lo, rescale_hi = min_val, max_val
        print(f"[LINEAR] Using linear scaling: {min_val},{max_val}")
    
    # Validate COG URL exists
    if not validate_cog_url(url):
        raise HTTPException(404, f"COG file not found or inaccessible: {url}")
    
    # Render tile using TiTiler's native expression support
    try:
        img = render_tile(
            path=url,
            z=z, x=x, y=y,
            min_value=rescale_lo, max_value=rescale_hi,
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
            "X-Dataset": dataset or "unknown",
            "X-Expression": expression,
            "X-Original-Rescale": f"{min_val},{max_val}",
            "X-Actual-Rescale": f"{rescale_lo},{rescale_hi}"
        },
    ) 