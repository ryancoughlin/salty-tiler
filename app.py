#!/usr/bin/env python
"""
TiTiler app to serve SST data from GOES19 ABI sensor

This application uses TiTiler to serve Cloud-Optimized GeoTIFF (COG) files
containing sea surface temperature data from the GOES19 ABI sensor.
"""
from fastapi import FastAPI
from titiler.core.factory import TilerFactory
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.dependencies import DatasetPathParams
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path

# Initialize the FastAPI app
app = FastAPI(
    title="ABI-GOES19 Sea Surface Temperature TiTiler",
    description="A TiTiler instance for serving ABI-GOES19 sea surface temperature data",
    version="0.1.0",
)

# Add CORS middleware to allow requests from anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Create a TilerFactory with default settings
cog = TilerFactory()

# Include the router with "/cog" prefix - this creates /cog/{z}/{x}/{y} routes
app.include_router(cog.router, prefix="/cog")

# Add basic endpoints to the root of the application
@app.get("/")
def root():
    """
    Root endpoint, confirming API is running and provides links to documentation
    """
    return {
        "message": "ABI-GOES19 Sea Surface Temperature TiTiler API is running",
        "documentation": "/docs",
        "cog_endpoint": "/cog",
        "preview_link": "/preview?url=data/ABI-GOES19-GLOBAL-2025-04-26T170000Z_SST_cog.tif"
    }

@app.get("/preview")
def preview(url: str = "data/ABI-GOES19-GLOBAL-2025-04-26T170000Z_SST_cog.tif"):
    """
    Create a preview link for the mapbox-viewer/index.html 
    pointing to the specified COG file
    """
    return {
        "message": "Use the following URL with the mapbox-viewer",
        "viewer_url": f"mapbox-viewer/index.html?url=http://localhost:8001/cog/tilejson.json?url={url}"
    }

# Add exception handlers
add_exception_handlers(app, DEFAULT_STATUS_CODES)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True) 