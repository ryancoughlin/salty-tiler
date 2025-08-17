#!/usr/bin/env python
"""
TiTiler app to serve SST data from GOES19 ABI sensor, chlorophyll, and other ocean datasets

This application uses TiTiler to serve Cloud-Optimized GeoTIFF (COG) files
containing sea surface temperature and chlorophyll data.
"""
from fastapi import FastAPI, Request
from titiler.core.factory import TilerFactory, ColorMapFactory
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from urllib.parse import urlencode, parse_qs, urlparse, urlunparse

# No heavy middleware imports

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

# No heavy middleware - keep it simple for performance

# Middleware to handle HTTP COG access issues
# @app.middleware("http")
# async def handle_cog_http_issues(request: Request, call_next):
#     """Handle HTTP COG access issues by downloading files locally when needed."""
#     import tempfile
#     import requests
#     import os
#     import hashlib
#     
#     # Only intercept COG tile requests
#     if "/cog/tiles/" in request.url.path:
#         # Get the URL parameter
#         url_param = request.query_params.get("url")
#         if url_param and url_param.startswith("http"):
#             # Check if this is a known problematic URL pattern
#             if "data.saltyoffshore.com" in url_param:
#                 # Create a local copy in temp directory
#                 temp_dir = "/tmp/cog_cache"
#                 os.makedirs(temp_dir, exist_ok=True)
#                 
#                 # Create a unique filename based on the full URL path to avoid region conflicts
#                 # Use hash of the URL to create unique cache key per region/dataset
#                 url_hash = hashlib.md5(url_param.encode()).hexdigest()
#                 filename = f"{url_hash}.tif"
#                 local_path = os.path.join(temp_dir, filename)
#                 
#                 # Check if file already exists locally
#                 if not os.path.exists(local_path):
#                     try:
#                         # Download the file
#                         response = requests.get(url_param, timeout=30)
#                         response.raise_for_status()
#                         
#                         with open(local_path, "wb") as f:
#                             f.write(response.content)
#                         
#                         print(f"[COG] Downloaded {url_param} to {local_path}")
#                     except Exception as e:
#                         print(f"[COG] Failed to download {url_param}: {e}")
#                         # Continue with original request
#                         return await call_next(request)
#                 
#                 # Replace the URL parameter with local path
#                 new_query_params = dict(request.query_params)
#                 new_query_params["url"] = f"file://{local_path}"
#                 
#                 # Reconstruct the request
#                 new_query_string = "&".join([f"{k}={v}" for k, v in new_query_params.items()])
#                 request.scope["query_string"] = new_query_string.encode()
#     
#     return await call_next(request)

# Middleware to strip bidx parameter from COG tile requests
@app.middleware("http")
async def strip_bidx_parameter(request: Request, call_next):
    """Strip bidx parameter from COG tile requests to handle iOS app's automatic bidx=1 addition."""
    
    # Only intercept COG tile requests
    if "/cog/tiles/" in request.url.path:
        # Check if bidx parameter exists
        if "bidx" in request.query_params:
            # Create new query params without bidx
            new_query_params = dict(request.query_params)
            removed_bidx = new_query_params.pop("bidx", None)
            
            if removed_bidx:
                print(f"[BIDX] Removed bidx={removed_bidx} from request")
                
                # Reconstruct the request without bidx
                new_query_string = "&".join([f"{k}={v}" for k, v in new_query_params.items()])
                request.scope["query_string"] = new_query_string.encode()
    
    return await call_next(request)

# Create a TilerFactory with the custom colormap and all standard endpoints
cog = TilerFactory(
    colormap_dependency=ColorMapParams,
    add_preview=True,
    add_part=True,
    add_viewer=True,
)

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