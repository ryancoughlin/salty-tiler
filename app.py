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

# Import required classes for custom algorithm
from titiler.core.algorithm import BaseAlgorithm, algorithms as default_algorithms
from rio_tiler.models import ImageData

class TemperatureConverter(BaseAlgorithm):
    """Convert temperature units from Celsius or Kelvin to Fahrenheit.
    
    The default behavior assumes input is in Celsius.
    To convert from Kelvin, set from_kelvin=True.
    """
    
    # Parameters with defaults
    from_kelvin: bool = False
    
    def __call__(self, img: ImageData) -> ImageData:
        # Deep copy the data to avoid modifying the original
        data = img.data.copy()
        
        # Convert the temperature values
        if self.from_kelvin:
            # Convert from Kelvin to Fahrenheit: F = (K - 273.15) * 9/5 + 32
            data = (data - 273.15) * 9/5 + 32
        else:
            # Convert from Celsius to Fahrenheit: F = C * 9/5 + 32
            data = data * 9/5 + 32
        
        # Create output ImageData with converted values
        return ImageData(
            data,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
        )

# Register the custom algorithm
algorithms = default_algorithms.register(
    {
        "fahrenheit": TemperatureConverter,
    }
)

# Initialize the FastAPI app
app = FastAPI(
    title="ABI-GOES19 Sea Surface Temperature TiTiler",
    description="A TiTiler instance for serving ABI-GOES19 sea surface temperature data with temperature conversion to Fahrenheit",
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

# Create a TilerFactory with the custom algorithms
cog = TilerFactory(process_dependency=algorithms.dependency)

# Include the router with "/cog" prefix - this creates /cog/{z}/{x}/{y} routes
app.include_router(cog.router, prefix="/cog")

# Add exception handlers
add_exception_handlers(app, DEFAULT_STATUS_CODES)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True) 