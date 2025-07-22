#!/usr/bin/env python
"""
TiTiler app to serve SST data from GOES19 ABI sensor, chlorophyll, and other ocean datasets

This application uses TiTiler to serve Cloud-Optimized GeoTIFF (COG) files
containing sea surface temperature and chlorophyll data.
"""
from fastapi import FastAPI
from titiler.core.factory import TilerFactory, ColorMapFactory
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

# Import TiTiler middleware for caching
from titiler.core.middleware import CacheControlMiddleware, TotalTimeMiddleware

# Import routes
from routes.metadata import router as metadata_router
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

# Add TiTiler middleware for caching
# For ocean data timeline scrubbing, we want tiles to be cached for a reasonable duration
# but not too long since data updates regularly
# 6 hours provides good balance between performance and data freshness for timeline scrubbing
cache_control_settings = "public, max-age=21600"  # 6 hour cache for tiles
app.add_middleware(CacheControlMiddleware, cachecontrol=cache_control_settings)
app.add_middleware(TotalTimeMiddleware)

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
app.include_router(metadata_router)
app.include_router(tiles_router)

# Health check endpoint for Docker
@app.get("/health")
def health_check():
    """Health check endpoint for load balancer and Docker."""
    return {"status": "healthy", "service": "salty-tiler"}

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