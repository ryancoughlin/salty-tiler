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
from typing import Dict, Tuple, Any, List
import uvicorn
import json
import os

# Import TiTiler middleware for caching
from titiler.core.middleware import CacheControlMiddleware, TotalTimeMiddleware

# Import routes
from routes.metadata import router as metadata_router
from routes.tiles import router as tiles_router

# Import color dependencies
from rio_tiler.colormap import cmap as default_cmap
from titiler.core.dependencies import create_colormap_dependency



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
    '#f96f27', '#f85e1f', '#f74d17', '#e6420e', '#d53e0d', 
    '#c43a0c', '#b3360b', '#a2320a', '#912e09', '#802a08', 
    '#6f2607', '#5e2206'
]

# Chlorophyll color scale
CHLOROPHYLL_COLORS = [
    "#0C0D6C", "#1A1A83", "#28289A", "#3535B1", "#4343C8",
    "#5050DF", "#5D5DF6", "#7070FF", "#8282FF", "#9494FF",
    
    "#2A9A8F", "#31A594", "#38B099", "#3FBB9E", "#46C6A3",
    "#4ECFAA", "#56D8B1", "#5EE1B8", "#66EABF", "#6EF3C6",
    
    "#76F9CD", "#88FAC5", "#9AFABD", "#ACFAB5", "#BFFA9D",
    "#D1FA95", "#E3FA8D", "#F5FA85", "#FAFD6D", "#FAED65",
    
    "#FADD5D", "#FAD455", "#FACA4D", "#FAC045", "#FAB73D",
    "#FAAD35", "#FAA32D", "#FA9925", "#FA8F1D", "#FA7A00"
]

# Salinity color scale
SALINITY_COLORS = [
    '#29186b',
    '#2b2f8e',
    '#224b9f',
    '#1972b5',
    '#1b9abe',
    '#25beca',
    '#52dbc1',
    '#8aeaa8',
    '#c5f298',
    '#f9f287'
]

# Water clarity (K490) color scale
WATER_CLARITY_COLORS = [
    '#00204c', '#002b66', '#003780', '#00439a', '#004fb4',
    '#005bce', '#0067e8', '#0073ff', '#198eff', '#32a9ff',
    '#4bc4ff', '#64dfff', '#7dffff', '#7dffef', '#7dffdf',
    '#7dffcf', '#7dffbf', '#7dffaf', '#7dff9f', '#7dff8f',
    '#66ff66', '#4fff4f', '#38ff38', '#21ff21', '#0aff0a'
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

# Generate the continuous colormaps
sst_colormap = create_continuous_colormap(SST_COLORS_HIGH_CONTRAST, 256)
chlorophyll_colormap = create_continuous_colormap(CHLOROPHYLL_COLORS, 256)
salinity_colormap = create_continuous_colormap(SALINITY_COLORS, 256)
water_clarity_colormap = create_continuous_colormap(WATER_CLARITY_COLORS, 256)

# Load palette from JSON
with open("sst_colormap.json") as f:
    custom_palette = json.load(f)

# Register custom colormaps
custom_colormaps = {
    "sst_high_contrast": sst_colormap,
    "chlorophyll": chlorophyll_colormap,
    "salinity": salinity_colormap,
    "water_clarity": water_clarity_colormap,
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