from fastapi import APIRouter, HTTPException, Response, Query, Path
from services.tiler import render_tile
import requests

router = APIRouter()

# Dataset default ranges (should match metadata.py)
DATASET_RANGES = {
    "sst": {"min": -2.0, "max": 35.0},
    "chlorophyll": {"min": 0.01, "max": 30.0},
}

def validate_cog_url(url: str) -> bool:
    """Validate that the COG URL is accessible and is a valid TIFF file."""
    try:
        # Quick HEAD request to check if URL exists and is accessible
        response = requests.head(url, timeout=10)
        return response.status_code == 200 and 'tif' in url.lower()
    except:
        return False

@router.get("/tiles/{dataset}/{region}/{timestamp}/{z}/{x}/{y}.png")
def tile_from_external_cog(
    dataset: str = Path(..., description="Dataset name (e.g., sst_composite)"),
    region: str = Path(..., description="Region name (e.g., ne_canyons)"),
    timestamp: str = Path(..., description="Timestamp (e.g., 2025-07-13T070646Z)"),
    z: int = Path(...),
    x: int = Path(...),
    y: int = Path(...),
    min: float | None = Query(None),
    max: float | None = Query(None),
    base_url: str = Query("https://data.saltyoffshore.com", description="Base URL for COG files"),
):
    """
    Render a PNG tile from an external COG URL.
    
    URL format: {base_url}/{region}/{dataset}/{timestamp}_cog.tif
    Example: https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif
    """
    # Construct the COG URL
    cog_filename = f"{timestamp}_cog.tif"
    cog_url = f"{base_url}/{region}/{dataset}/{cog_filename}"
    
    # Validate COG URL exists
    if not validate_cog_url(cog_url):
        raise HTTPException(404, f"COG file not found or inaccessible: {cog_url}")
    
    # Determine dataset type from dataset name for range validation
    dataset_type = "sst" if "sst" in dataset.lower() else "chlorophyll" if "chlor" in dataset.lower() else "sst"
    
    # Validate min/max ranges
    range_info = DATASET_RANGES.get(dataset_type, DATASET_RANGES["sst"])
    lo, hi = range_info["min"], range_info["max"]
    min_val = lo if min is None else min
    max_val = hi if max is None else max
    
    if not (lo <= min_val < max_val <= hi):
        raise HTTPException(400, f"min/max must satisfy {lo} ≤ min < max ≤ {hi}")
    
    # Render tile from external COG URL
    try:
        img = render_tile(
            path=cog_url,
            z=z, x=x, y=y,
            min_value=min_val, max_value=max_val,
            colormap_name="sst_high_contrast" if dataset_type == "sst" else "custom_palette",
            colormap_bins=256,
        )
    except Exception as e:
        raise HTTPException(404, f"Tile not available: {str(e)}")

    return Response(
        img,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-COG-URL": cog_url,
        },
    )

@router.get("/tiles/{z}/{x}/{y}.png")
def tile_from_url(
    z: int = Path(...),
    x: int = Path(...),
    y: int = Path(...),
    url: str = Query(..., description="Full URL to COG file"),
    min: float | None = Query(None),
    max: float | None = Query(None),
    dataset: str = Query("sst", description="Dataset type for range validation"),
):
    """
    Render a PNG tile from a direct COG URL.
    
    Example: /tiles/6/12/20.png?url=https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif&min=32&max=86
    """
    # Validate COG URL exists
    if not validate_cog_url(url):
        raise HTTPException(404, f"COG file not found or inaccessible: {url}")
    
    # Validate min/max ranges
    range_info = DATASET_RANGES.get(dataset, DATASET_RANGES["sst"])
    lo, hi = range_info["min"], range_info["max"]
    min_val = lo if min is None else min
    max_val = hi if max is None else max
    
    if not (lo <= min_val < max_val <= hi):
        raise HTTPException(400, f"min/max must satisfy {lo} ≤ min < max ≤ {hi}")
    
    # Render tile from external COG URL
    try:
        img = render_tile(
            path=url,
            z=z, x=x, y=y,
            min_value=min_val, max_value=max_val,
            colormap_name="sst_high_contrast" if dataset == "sst" else "custom_palette",
            colormap_bins=256,
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