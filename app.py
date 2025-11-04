#!/usr/bin/env python
"""
TiTiler app to serve SST data from GOES19 ABI sensor, chlorophyll, and other ocean datasets

This application uses TiTiler to serve Cloud-Optimized GeoTIFF (COG) files
containing sea surface temperature and chlorophyll data.
"""
from contextlib import asynccontextmanager
import os

# Configure GDAL for S3-compatible storage BEFORE importing any GDAL-dependent libraries
# This must happen before rasterio/titiler imports
from services.storage import configure_gdal_for_s3
configure_gdal_for_s3()

from fastapi import FastAPI
from titiler.core.factory import ColorMapFactory
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import routes
from routes.tiles import router as tiles_router

# Import color service
from services.colors import register_colormaps

# Import MosaicJSON support
from titiler.mosaic.factory import MosaicTilerFactory

# Import custom algorithms
from algorithms import (Log10, Log10Chlorophyll, SqrtChlorophyll, GammaChlorophyll,
                        LinearChlorophyll, ChlorophyllRangeMapper, ChlorophyllSmoothMapper,
                        OceanMask)


# Register all colormaps
ColorMapParams, cmap = register_colormaps()

# Register custom algorithms
from titiler.core.algorithm import algorithms as default_algorithms
from titiler.core.algorithm import Algorithms

algorithms: Algorithms = default_algorithms.register({
    "log10": Log10,
    "log10_chlorophyll": Log10Chlorophyll,
    "sqrt_chlorophyll": SqrtChlorophyll,
    "gamma_chlorophyll": GammaChlorophyll,
    "linear_chlorophyll": LinearChlorophyll,
    "chlorophyll_range_mapper": ChlorophyllRangeMapper,
    "chlorophyll_smooth_mapper": ChlorophyllSmoothMapper,
    "ocean_mask": OceanMask,
})

# Create algorithm dependency
PostProcessParams = algorithms.dependency


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources on app startup and shutdown."""
    # Startup: Initialize GDAL configuration and cache
    # Configure GDAL for optimal performance based on TiTiler recommendations
    # https://developmentseed.org/titiler/advanced/performance_tuning/

    # Log current GDAL configuration (set by Docker)
    gdal_vars = [
        "GDAL_DISABLE_READDIR_ON_OPEN", "GDAL_CACHEMAX", "CPL_VSIL_CURL_CACHE_SIZE",
        "VSI_CACHE", "VSI_CACHE_SIZE", "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES",
        "GDAL_HTTP_MULTIPLEX", "GDAL_HTTP_VERSION", "GDAL_BAND_BLOCK_CACHE"
    ]

    print("[GDAL] Configuration:")
    for var in gdal_vars:
        value = os.getenv(var, "Not set")
        print(f"  {var}={value}")

    # Log S3/DigitalOcean Spaces configuration
    spaces_vars = [
        "SPACES_ACCESS_KEY_ID", "SPACES_SECRET_ACCESS_KEY", "SPACES_ENDPOINT",
        "SPACES_BUCKET", "SPACES_REGION", "SPACES_CDN_URL"
    ]
    aws_vars = [
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
        "AWS_REGION", "AWS_S3_ENDPOINT"
    ]
    
    print("[Spaces] Configuration:")
    has_spaces = False
    for var in spaces_vars:
        value = os.getenv(var, "Not set")
        if value != "Not set":
            has_spaces = True
        # Mask secrets for security
        if "SECRET" in var or "KEY" in var:
            value = "***" if value != "Not set" else value
        print(f"  {var}={value}")
    
    if not has_spaces:
        print("[S3] Configuration (AWS fallback):")
        for var in aws_vars:
            value = os.getenv(var, "Not set")
            # Mask secrets for security
            if "SECRET" in var or "TOKEN" in var or "KEY" in var:
                value = "***" if value != "Not set" else value
            print(f"  {var}={value}")
    
    # Check if credentials are configured (after mapping)
    has_creds = bool(os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("SPACES_ACCESS_KEY_ID"))
    has_endpoint = bool(os.getenv("AWS_S3_ENDPOINT") or os.getenv("SPACES_ENDPOINT"))
    
    if has_endpoint and not has_creds:
        print("[S3] ⚠️  Warning: S3 endpoint is configured but credentials are missing.")
        print("[S3]   HTTP URLs will work, but VSI paths will require credentials.")

    yield  # Application runs here

    # Shutdown: cleanup if needed (none currently required)


# Initialize the FastAPI app with lifespan
app = FastAPI(
    title="Salty Tiler: Ocean Data TiTiler",
    description="A TiTiler instance for serving temperature and chlorophyll data with temperature conversion to Fahrenheit",
    version="0.1.0",
    lifespan=lifespan,
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

# Add TiTiler's built-in cache control middleware
try:
    from titiler.core.middleware import CacheControlMiddleware
    app.add_middleware(CacheControlMiddleware, cachecontrol="public, max-age=86400")
    print("[CACHE] Added CacheControlMiddleware")
except ImportError:
    print("[CACHE] CacheControlMiddleware not available")

# Create a TilerFactory with the custom colormap, algorithms and all standard endpoints
from titiler.core.factory import TilerFactory
cog = TilerFactory(
    colormap_dependency=ColorMapParams,
    process_dependency=PostProcessParams,
    add_preview=True,
    add_part=True,
    add_viewer=True,
)

# Create MosaicTilerFactory with custom colormaps
mosaic = MosaicTilerFactory(colormap_dependency=ColorMapParams)

# Create a ColorMapFactory to expose colormap discovery endpoints
colormap_factory = ColorMapFactory(supported_colormaps=cmap)

# Include the router with "/cog" prefix - this creates /cog/{z}/{x}/{y} routes
app.include_router(cog.router, prefix="/cog", tags=["Cloud Optimized GeoTIFF"])

# Include the mosaic router with "/mosaicjson" prefix - this creates /mosaicjson/{z}/{x}/{y} routes
app.include_router(mosaic.router, prefix="/mosaicjson", tags=["MosaicJSON"])

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