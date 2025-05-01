#!/usr/bin/env python
"""
TiTiler app to serve SST data from GOES19 ABI sensor

This application uses TiTiler to serve Cloud-Optimized GeoTIFF (COG) files
containing sea surface temperature data from the GOES19 ABI sensor.
"""
from fastapi import FastAPI
from titiler.core.factory import TilerFactory
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path

# Initialize the FastAPI app
app = FastAPI(
    title="ABI-GOES19 Sea Surface Temperature TiTiler",
    description="A TiTiler instance for serving ABI-GOES19 sea surface temperature data with a fixed color palette",
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

# Add exception handlers
add_exception_handlers(app, DEFAULT_STATUS_CODES)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True) 