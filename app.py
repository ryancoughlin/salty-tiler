#!/usr/bin/env python
"""
TiTiler app to serve SST data from GOES19 ABI sensor, chlorophyll, and other ocean datasets

This application uses TiTiler to serve Cloud-Optimized GeoTIFF (COG) files
containing sea surface temperature and chlorophyll data.
"""
from fastapi import FastAPI
from titiler.core.factory import TilerFactory
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Tuple, Any, List
import uvicorn
from pathlib import Path
import numpy as np
import json

# Import routes
from routes.metadata import router as metadata_router
from routes.tiles import router as tiles_router

# Import color dependencies
from rio_tiler.colormap import cmap as default_cmap
from titiler.core.dependencies import create_colormap_dependency

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

# Define custom SST color map based on user's high contrast palette
# Convert the list of hex colors to a continuous colormap
def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# User's high contrast color scale
SST_COLORS_HIGH_CONTRAST = [
    '#081d58', '#0d2167', '#122b76', '#173584', '#1c3f93',
    '#2149a1', 
    '#3a7bea', '#4185f8',
    '#34d1db', 
    '#0effc5', 
    '#7ff000', 
    '#ebf600', 
    '#fec44f', '#fdb347', '#fca23f', '#fb9137', '#fa802f',
    '#f96f27', '#f85e1f', '#f74d17'
]

# Create a fully interpolated colormap with 256 colors
def create_continuous_colormap(color_list: List[str], num_colors: int = 500) -> Dict[int, Tuple[int, int, int, int]]:
    """Create a continuous colormap by interpolating between colors in the list."""
    # Convert hex colors to RGB
    rgb_colors = [hex_to_rgb(color) for color in color_list]
    
    # Number of color segments
    num_segments = len(rgb_colors) - 1
    
    # Calculate how many colors to generate per segment
    colors_per_segment = [num_colors // num_segments] * num_segments
    # Distribute any remainder
    remainder = num_colors % num_segments
    for i in range(remainder):
        colors_per_segment[i] += 1
    
    # Generate the continuous colormap
    continuous_map = {}
    color_index = 0
    
    for segment in range(num_segments):
        r1, g1, b1 = rgb_colors[segment]
        r2, g2, b2 = rgb_colors[segment + 1]
        
        for i in range(colors_per_segment[segment]):
            # Calculate interpolation factor
            t = i / (colors_per_segment[segment] - 1) if colors_per_segment[segment] > 1 else 0
            
            # Linear interpolation between colors
            r = int(r1 * (1 - t) + r2 * t)
            g = int(g1 * (1 - t) + g2 * t)
            b = int(b1 * (1 - t) + b2 * t)
            
            # Add to colormap with full opacity
            continuous_map[color_index] = (r, g, b, 255)
            color_index += 1
    
    return continuous_map

# Generate the continuous colormap
sst_colormap = create_continuous_colormap(SST_COLORS_HIGH_CONTRAST, 256)

# Load palette from JSON
with open("my_palette.json") as f:
    custom_palette = json.load(f)

# Register custom colormaps
custom_colormaps = {
    "sst_high_contrast": sst_colormap,
    "custom_palette": custom_palette
}

# Register the custom colormap with rio-tiler
cmap = default_cmap.register(custom_colormaps)
ColorMapParams = create_colormap_dependency(cmap)

# Initialize the FastAPI app
app = FastAPI(
    title="Salty Tiler: Ocean Data TiTiler",
    description="A TiTiler instance for serving temperature and chlorophyll data with temperature conversion to Fahrenheit",
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

# Create a TilerFactory with the custom algorithms and colormap
cog = TilerFactory(
    process_dependency=algorithms.dependency,
    colormap_dependency=ColorMapParams
)

# Include the router with "/cog" prefix - this creates /cog/{z}/{x}/{y} routes
app.include_router(cog.router, prefix="/cog")

# Register application-specific routers
app.include_router(metadata_router)
app.include_router(tiles_router)

# Add exception handlers
add_exception_handlers(app, DEFAULT_STATUS_CODES)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True) 