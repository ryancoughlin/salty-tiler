#!/usr/bin/env python
"""
Color management service for ocean data visualization

This module handles all color scale registration and management for the TiTiler application,
including SST, chlorophyll, salinity, and water clarity color scales.
"""
from typing import Dict, Tuple, List
import json
from rio_tiler.colormap import cmap as default_cmap
from titiler.core.dependencies import create_colormap_dependency


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

# Chlorophyll color scale - High contrast for fishing contours
CHLOROPHYLL_COLORS = [
    "#001F3F",  # 0.00 - Deep ocean blue
    "#0066CC",  # 1.33 - Ocean blue
    "#00CCFF",  # 2.67 - Cyan blue
    "#00CC66",  # 3.20 - Green
    "#FFD700",  # 3.73 - Gold
    "#FF8C42",  # 4.00 - Coral (high productivity)
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


def load_custom_colormaps() -> Dict[str, Dict[int, Tuple[int, int, int, int]]]:
    """Load and register all custom colormaps."""
    # Generate the continuous colormaps
    sst_colormap = create_continuous_colormap(SST_COLORS_HIGH_CONTRAST, 256)
    chlorophyll_colormap = create_continuous_colormap(CHLOROPHYLL_COLORS, 256)
    salinity_colormap = create_continuous_colormap(SALINITY_COLORS, 256)
    water_clarity_colormap = create_continuous_colormap(WATER_CLARITY_COLORS, 256)
    
    # Load palette from JSON
    try:
        with open("sst_colormap.json") as f:
            custom_palette = json.load(f)
    except FileNotFoundError:
        # Fallback to empty dict if file doesn't exist
        custom_palette = {}
    
    # Register custom colormaps
    custom_colormaps = {
        "sst_high_contrast": sst_colormap,
        "chlorophyll": chlorophyll_colormap,
        "salinity": salinity_colormap,
        "water_clarity": water_clarity_colormap,
        "custom_palette": custom_palette
    }
    
    return custom_colormaps


def register_colormaps():
    """Register all colormaps with rio-tiler and return the dependency."""
    custom_colormaps = load_custom_colormaps()
    
    # Register the custom colormap with rio-tiler
    cmap = default_cmap.register(custom_colormaps)
    ColorMapParams = create_colormap_dependency(cmap)
    
    return ColorMapParams, cmap