"""
Bathymetry-specific routes for MosaicJSON endpoints and crosshair depth queries.

This module provides endpoints for:
- Bathymetry tile rendering from MosaicJSON
- Crosshair depth value queries
- Bathymetry-specific metadata and statistics
"""
from fastapi import APIRouter, HTTPException, Query, Path, Response
from typing import Optional, Tuple
from cache_plugin import cached
import requests
import hashlib
from services.tiler import render_mosaic_tile, query_mosaic_point

router = APIRouter()

def validate_mosaic_url(url: str) -> bool:
    """Validate that the MosaicJSON URL is accessible."""
    try:
        response = requests.head(url, timeout=10)
        return response.status_code == 200 and url.endswith('.json')
    except:
        return False

def generate_mosaic_cache_key(url: str, z: int, x: int, y: int, rescale: str, colormap_name: str) -> str:
    """Generate cache key for mosaic tile requests."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    rescale_hash = hashlib.md5(rescale.encode()).hexdigest()[:6]
    return f"mosaic:{url_hash}:{z}:{x}:{y}:{rescale_hash}:{colormap_name}"

@router.get("/mosaicjson/tiles/{z}/{x}/{y}.png")
@cached(alias="default")
def mosaic_tile(
    z: int = Path(..., ge=0, le=18, description="Zoom level"),
    x: int = Path(..., description="Tile X coordinate"),
    y: int = Path(..., description="Tile Y coordinate"),
    url: str = Query(..., description="URL to MosaicJSON file"),
    rescale: str = Query(..., description="Min,max range for rescaling (e.g., -5000,0)"),
    colormap_name: str = Query(..., description="Colormap name (e.g., bathymetry)"),
    resampling: str = Query("bilinear", description="Resampling method"),
):
    """
    Render bathymetry tiles from MosaicJSON.
    
    This endpoint serves bathymetry tiles from a MosaicJSON manifest that points
    to multiple regional COG files. Perfect for serving large bathymetry datasets
    split into manageable regional chunks.
    
    Example: /mosaicjson/tiles/6/12/20.png?url=https://data.saltyoffshore.com/bathy/gebco_mosaic.json&rescale=-5000,0&colormap_name=bathymetry
    """
    # Parse rescale parameter
    try:
        min_val, max_val = map(float, rescale.split(','))
    except ValueError:
        raise HTTPException(400, "rescale parameter must be in format 'min,max'")
    
    # Validate MosaicJSON URL
    if not validate_mosaic_url(url):
        raise HTTPException(404, f"MosaicJSON file not found or inaccessible: {url}")
    
    # Render tile from mosaic
    try:
        img = render_mosaic_tile(
            mosaic_url=url,
            z=z, x=x, y=y,
            min_value=min_val, max_value=max_val,
            colormap_name=colormap_name,
            colormap_bins=256,
            resampling=resampling,
        )
    except Exception as e:
        raise HTTPException(404, f"Tile not available: {str(e)}")

    # Generate cache key for debugging
    cache_key = generate_mosaic_cache_key(url, z, x, y, rescale, colormap_name)
    
    return Response(
        img,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Mosaic-URL": url,
            "X-Rescale": f"{min_val},{max_val}",
            "X-Cache-Key": cache_key,
            "X-Tile-Coords": f"{z}/{x}/{y}"
        },
    )

@router.get("/mosaicjson/point/{lon},{lat}")
@cached(alias="default")
def mosaic_point_query(
    lon: float = Path(..., ge=-180, le=180, description="Longitude"),
    lat: float = Path(..., ge=-90, le=90, description="Latitude"),
    url: str = Query(..., description="URL to MosaicJSON file"),
):
    """
    Query bathymetry depth at a specific coordinate from MosaicJSON.
    
    This is the key endpoint for crosshair depth queries in your iOS app.
    Returns the exact bathymetry depth value at the specified coordinate,
    automatically handling which regional COG contains the data.
    
    Example: /mosaicjson/point/-74.5,40.2?url=https://data.saltyoffshore.com/bathy/gebco_mosaic.json
    
    Returns:
    {
        "coordinates": [-74.5, 40.2],
        "values": [{"band": 1, "value": -1234.5}],
        "depth_meters": -1234.5
    }
    """
    # Validate MosaicJSON URL
    if not validate_mosaic_url(url):
        raise HTTPException(404, f"MosaicJSON file not found or inaccessible: {url}")
    
    # Query point value from mosaic
    try:
        result = query_mosaic_point(
            mosaic_url=url,
            lon=lon, lat=lat,
        )
        
        # Extract depth value (assuming single band)
        depth_value = result.get("values", [{}])[0].get("value", None)
        
        return {
            "coordinates": [lon, lat],
            "values": result.get("values", []),
            "depth_meters": depth_value,
            "mosaic_url": url
        }
        
    except Exception as e:
        raise HTTPException(404, f"Point query failed: {str(e)}")

@router.get("/mosaicjson/info")
@cached(alias="default")
def mosaic_info(
    url: str = Query(..., description="URL to MosaicJSON file"),
):
    """
    Get metadata about a MosaicJSON file.
    
    Returns information about the mosaic including bounds, zoom levels,
    and constituent COG files. Useful for setting up your iOS app's
    map bounds and zoom constraints.
    
    Example: /mosaicjson/info?url=https://data.saltyoffshore.com/bathy/gebco_mosaic.json
    """
    # Validate MosaicJSON URL
    if not validate_mosaic_url(url):
        raise HTTPException(404, f"MosaicJSON file not found or inaccessible: {url}")
    
    try:
        # Fetch and parse MosaicJSON
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        mosaic_data = response.json()
        
        return {
            "mosaicjson": mosaic_data.get("mosaicjson", "0.0.2"),
            "version": mosaic_data.get("version", "1.0.0"),
            "name": mosaic_data.get("name", "Bathymetry Mosaic"),
            "description": mosaic_data.get("description", "Regional bathymetry data"),
            "minzoom": mosaic_data.get("minzoom", 0),
            "maxzoom": mosaic_data.get("maxzoom", 18),
            "bounds": mosaic_data.get("bounds"),
            "center": mosaic_data.get("center"),
            "tiles": mosaic_data.get("tiles", []),
            "tile_count": len(mosaic_data.get("tiles", [])),
            "url": url
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch mosaic info: {str(e)}")

@router.get("/mosaicjson/statistics")
@cached(alias="default")
def mosaic_statistics(
    url: str = Query(..., description="URL to MosaicJSON file"),
    bbox: Optional[str] = Query(None, description="Bounding box as 'minx,miny,maxx,maxy'"),
):
    """
    Get statistics for bathymetry data in a MosaicJSON.
    
    Optionally filter by bounding box. Useful for determining
    appropriate rescale ranges for your iOS app.
    
    Example: /mosaicjson/statistics?url=https://data.saltyoffshore.com/bathy/gebco_mosaic.json&bbox=-75,-40,-70,-35
    """
    # Validate MosaicJSON URL
    if not validate_mosaic_url(url):
        raise HTTPException(404, f"MosaicJSON file not found or inaccessible: {url}")
    
    try:
        # Parse bbox if provided
        bbox_coords = None
        if bbox:
            try:
                coords = list(map(float, bbox.split(',')))
                if len(coords) != 4:
                    raise ValueError("bbox must have 4 coordinates")
                bbox_coords = coords
            except ValueError:
                raise HTTPException(400, "bbox must be in format 'minx,miny,maxx,maxy'")
        
        # This would typically use TiTiler's statistics endpoint
        # For now, return a placeholder response
        return {
            "url": url,
            "bbox": bbox_coords,
            "statistics": {
                "min": -5000.0,
                "max": 0.0,
                "mean": -2500.0,
                "std": 1250.0,
                "count": 1000000
            },
            "note": "Statistics endpoint - implement with TiTiler statistics API"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Failed to get statistics: {str(e)}")
