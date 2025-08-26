#!/usr/bin/env python
"""
TiTiler app to serve SST data from GOES19 ABI sensor, chlorophyll, and other ocean datasets

This application uses TiTiler to serve Cloud-Optimized GeoTIFF (COG) files
containing sea surface temperature and chlorophyll data.
"""
from fastapi import FastAPI, Request
from titiler.core.factory import ColorMapFactory
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from urllib.parse import urlencode, parse_qs, urlparse, urlunparse

# Import caching
from cache import setup_cache, cached

# Import routes
from routes.tiles import router as tiles_router

# Import color service
from services.colors import register_colormaps


# Register all colormaps
ColorMapParams, cmap = register_colormaps()

# Initialize the FastAPI app
app = FastAPI(
    title="Salty Tiler: Ocean Data TiTiler",
    description="A TiTiler instance for serving temperature and chlorophyll data with temperature conversion to Fahrenheit",
    version="0.1.0",
)

# Setup cache on startup (1 day TTL = 86400 seconds)
@app.on_event("startup")
async def startup_event():
    """Initialize cache on application startup."""
    setup_cache(ttl=86400)  # 24 hours cache

# Configure CORS from environment variables
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
cors_methods = os.getenv("CORS_METHODS", "GET,POST,OPTIONS").split(",")
cors_headers = os.getenv("CORS_HEADERS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)

# Add TiTiler's built-in cache control middleware
try:
    from titiler.core.middleware import CacheControlMiddleware
    app.add_middleware(CacheControlMiddleware, cachecontrol="public, max-age=86400")
    print("[CACHE] Added CacheControlMiddleware")
except ImportError:
    print("[CACHE] CacheControlMiddleware not available")

# Create a TilerFactory with the custom colormap and all standard endpoints
from titiler.core.factory import TilerFactory
cog = TilerFactory(
    colormap_dependency=ColorMapParams,
    add_preview=True,
    add_part=True,
    add_viewer=True,
)

# Apply caching to tile routes after they're registered
def apply_caching_to_routes():
    """Apply caching to tile routes after they're registered."""
    for route in cog.router.routes:
        if hasattr(route, 'path') and '/tiles/' in route.path and hasattr(route, 'endpoint'):
            # Wrap the endpoint with caching
            original_endpoint = route.endpoint
            route.endpoint = cached(alias="default")(original_endpoint)
            print(f"[CACHE] Applied caching to route: {route.path}")

# Apply caching to routes
apply_caching_to_routes()

# Create a ColorMapFactory to expose colormap discovery endpoints
colormap_factory = ColorMapFactory(supported_colormaps=cmap)

# Include the router with "/cog" prefix - this creates /cog/{z}/{x}/{y} routes
app.include_router(cog.router, prefix="/cog", tags=["Cloud Optimized GeoTIFF"])

# Include the colormap router - this creates /colormaps endpoints
app.include_router(colormap_factory.router, tags=["ColorMaps"])

# Register application-specific routers
app.include_router(tiles_router)

# Health check endpoint for Docker
@app.get("/health")
def health_check():
    """Health check endpoint for load balancer and Docker."""
    return {"status": "healthy", "service": "salty-tiler"}

# Simple COG info endpoint (no caching)
@app.get("/cog/info")
async def cog_info(url: str):
    """Get COG information."""
    from rio_tiler.io import COGReader
    
    try:
        with COGReader(url) as cog:
            return {
                "bounds": cog.bounds,
                "center": cog.center,
                "minzoom": cog.minzoom,
                "maxzoom": cog.maxzoom,
                "band_names": cog.band_names,
                "dtype": str(cog.dataset.dtypes[0])
            }
    except Exception as e:
        return {"error": str(e)}

# Add exception handlers
add_exception_handlers(app, DEFAULT_STATUS_CODES)

# Debug endpoint to check COG file format and bands
@app.get("/debug/bands")
async def debug_cog_bands(url: str):
    """
    Debug endpoint to check COG file format and band information.
    Example: /debug/bands?url=https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-19T050224Z_cog.tif
    """
    import subprocess
    import tempfile
    import requests
    
    try:
        # Download a sample of the file to test
        response = requests.get(url, headers={'Range': 'bytes=0-2048'}, timeout=10)
        if response.status_code != 206:
            return {"error": f"HTTP {response.status_code}: Cannot access file"}
        
        # Save to temp file for GDAL to test
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name
        
        # Test with gdalinfo to get band information
        result = subprocess.run(
            ["gdalinfo", tmp_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Clean up temp file
        import os
        os.unlink(tmp_path)
        
        if result.returncode == 0:
            # Parse the output to extract band information
            output = result.stdout
            bands = []
            current_band = None
            
            for line in output.split('\n'):
                if line.strip().startswith('Band '):
                    current_band = line.strip()
                    bands.append(current_band)
                elif current_band and line.strip().startswith('  '):
                    bands.append(line.strip())
            
            return {
                "url": url,
                "status": "success",
                "file_size": len(response.content),
                "gdalinfo_output": output,
                "bands": bands,
                "band_count": len([b for b in bands if b.startswith('Band ')])
            }
        else:
            return {
                "url": url,
                "status": "error",
                "returncode": result.returncode,
                "stderr": result.stderr,
                "file_size": len(response.content)
            }
    except Exception as e:
        return {
            "url": url,
            "status": "exception",
            "error": str(e),
            "type": type(e).__name__
        }

# Debug endpoint to test full file access
@app.get("/debug/full")
async def debug_full_file(url: str):
    """
    Debug endpoint to test full file access and HTTP headers.
    Example: /debug/full?url=https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-19T050224Z_cog.tif
    """
    import requests
    import subprocess
    import tempfile
    
    try:
        # Test full file download
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}: Cannot download full file"}
        
        # Save full file to temp
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name
        
        # Test with gdalinfo on full file
        result = subprocess.run(
            ["gdalinfo", tmp_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Clean up temp file
        import os
        os.unlink(tmp_path)
        
        if result.returncode == 0:
            return {
                "url": url,
                "status": "success",
                "file_size": len(response.content),
                "headers": dict(response.headers),
                "gdalinfo_output": result.stdout[:500]  # First 500 chars
            }
        else:
            return {
                "url": url,
                "status": "gdal_error",
                "returncode": result.returncode,
                "stderr": result.stderr,
                "file_size": len(response.content)
            }
    except Exception as e:
        return {
            "url": url,
            "status": "exception",
            "error": str(e),
            "type": type(e).__name__
        }

if __name__ == "__main__":
    host = os.getenv("TILER_HOST", "0.0.0.0")
    port = int(os.getenv("TILER_PORT", "8001"))
    workers = int(os.getenv("WORKERS", "1"))
    
    uvicorn.run(
        "app:app", 
        host=host, 
        port=port, 
        workers=workers,
        reload=os.getenv("DEBUG", "false").lower() == "true"
    ) 