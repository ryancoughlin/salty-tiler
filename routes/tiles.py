from fastapi import APIRouter, HTTPException, Response, Query, Path
from typing import Any
from mock_supabase import get_entry_by_id
from services.tiler import render_tile
import json

router = APIRouter()

# Load palette at import (assume my_palette.json is in project root)
with open("my_palette.json") as f:
    CUSTOM_PALETTE = json.load(f)

# Dataset default ranges (should match metadata.py)
DATASET_RANGES = {
    "sst": {"min": -2.0, "max": 35.0},
    "chlorophyll": {"min": 0.01, "max": 30.0},
}

@router.get("/tiles/{entry_id}/{z}/{x}/{y}.png")
def tile_by_entry(
    entry_id: str = Path(..., description="Supabase entry UUID"),
    z: int = Path(...),
    x: int = Path(...),
    y: int = Path(...),
    layer: str = Query("geotiff", description="Layer key in entry layers JSON"),
    min: float | None = Query(None),
    max: float | None = Query(None),
):
    """
    Look up entry by entry_id, validate, and render a PNG tile from the COG using TiTiler.
    Replace mock_supabase with real Supabase integration in production.
    """
    entry = get_entry_by_id(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")

    dataset = entry["dataset_id"]
    layers = entry["layers"]
    cog_info = layers.get(layer)
    if not cog_info:
        raise HTTPException(400, f"Layer '{layer}' missing")
    path = cog_info["path"]

    # Validate min/max
    lo, hi = DATASET_RANGES.get(dataset, {}).values()
    min_val = lo if min is None else min
    max_val = hi if max is None else max
    if not (lo <= min_val < max_val <= hi):
        raise HTTPException(400, f"min/max must satisfy {lo} ≤ min < max ≤ {hi}")

    # Render tile
    try:
        img = render_tile(
            path=path,
            z=z, x=x, y=y,
            min_value=min_val, max_value=max_val,
            colormap=CUSTOM_PALETTE,
            colormap_bins=256,
        )
    except Exception:
        raise HTTPException(404, "Tile not available")

    return Response(
        img,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    ) 