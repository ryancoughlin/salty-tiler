#!/usr/bin/env python
"""
Color management service for ocean data visualization

This module handles all color scale registration and management for the TiTiler application,
including SST, chlorophyll, salinity, and water clarity color scales.
"""
from typing import Dict, Tuple, List
from rio_tiler.colormap import cmap as default_cmap
from titiler.core.dependencies import create_colormap_dependency


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


# User's high contrast color scale (evenly spaced, visually uniform)
SST_COLORS_HIGH_CONTRAST = [
    # Deep blue to blue
    '#081d58', '#16306e', '#21449b', '#2c5fcf', '#3883f6',
    # Cyan to green
    '#34d1db', '#0effc5', '#7ff000', '#ebf600',
    # Yellow to orange
    '#fec44f', '#fca23f', '#fb9137', '#fa802f', '#f96f27',
    # Orange-red to red
    '#f85e1f', '#f74d17', '#e6420e', '#d53e0d',
    # Red-brown to brown
    '#c43a0c', '#b3360b', '#a2320a', '#912e09', '#802a08',
    # Brown to dark brown
    '#6f2607', '#5e2206'
]

# Salty Vibes SST color scale - Ocean-inspired gradient
SST_COLORS_SALTY_VIBES = [
    # Deep ocean blues
    '#0d1554', '#0f1960', '#121e6c', '#142378', '#172884',
    '#192d90', '#1c329c', '#1e37a8', '#213db4', '#2342c0',
    
    # Transitional blues to cyans
    '#2647cc', '#264fd8', '#3057e4', '#415fe4', '#5267e4',
    '#6370e4', '#747ae4', '#8585e4', '#968fe4', '#a799e4',
    
    # Ocean teals and greens
    '#68c9bf', '#5ecfb9', '#55d5b2', '#4ddcac', '#44e2a5',
    '#3ce99f', '#33ef98', '#2bf691', '#22fc8b', '#1aff85',
    
    # Warm yellows
    '#c7e8b4', '#d3eaa6', '#e0ec97', '#ecee89', '#f9f07b',
    '#fff267', '#ffe854', '#ffdf41', '#ffd52e', '#ffcc1a',
    
    # Hot oranges
    '#ffbe17', '#ffb114', '#ffa412', '#ff970f', '#ff8a0d',
    '#ff7d0a', '#ff7008', '#fd6307', '#f95505', '#f64804',
    
    # Intense reds
    '#f33b02', '#eb2e01', '#e32100', '#dd1500', '#d60800',
    '#cf0003', '#be000a', '#ad0011', '#9c0018', '#8b001f'
]

# Original linear color scheme (0.00 to 2.00 mg/m³)
CHLOROPHYLL_COLORS = [
    '#8B3A8B',  # 0.00 mg/m³ - bright indigo/pink mix (ultra-oligotrophic Gulf Stream look)
    '#1a1a4b',  # 0.02 mg/m³ - deep indigo-blue transition
    '#0B3D91',  # 0.05 mg/m³ - deep blue
    '#0d5bb8',  # 0.10 mg/m³ - blue
    '#1464F4',  # 0.20 mg/m³ - blue
    '#1e7ee8',  # 0.35 mg/m³ - blue to blue-cyan
    '#00B3B3',  # 0.50 mg/m³ - cyan
    '#3fd1c7',  # 0.75 mg/m³ - light cyan
    '#F1C40F',  # 1.00 mg/m³ - yellow (productive edge)
    '#e6b800',  # 1.50 mg/m³ - yellow-orange
    '#D35400',  # 2.00 mg/m³ - orange-brown (upper end)
]

# Final optimized chlorophyll color scheme with ultra-smooth transitions
# Gulf Stream colors for low values, seamless blue→cyan→green→yellow progression
CHLOROPHYLL_COLORS = [
    '#8B3A8B',  # 0.00 mg/m³ - Ultra-clear Gulf Stream (purple-pink)
    '#6B238E',  # 0.01 mg/m³ - Transition
    '#4B1390',  # 0.02 mg/m³ - Ultra-clear transition
    '#2D1B69',  # 0.03 mg/m³ - Clear waters start (indigo)
    '#1a1a4b',  # 0.05 mg/m³ - Deep blue
    '#0f2a6b',  # 0.07 mg/m³ - Deep blue transition
    '#0B3D91',  # 0.10 mg/m³ - Medium blue
    '#0d5bb8',  # 0.15 mg/m³ - Medium blue
    '#1464F4',  # 0.20 mg/m³ - Bright blue
    '#1a71e1',  # 0.25 mg/m³ - Blue-cyan transition start
    '#1e7ee8',  # 0.30 mg/m³ - Blue-cyan
    '#2b8bc7',  # 0.40 mg/m³ - Blue-cyan
    '#00B3B3',  # 0.55 mg/m³ - Cyan
    '#26c4b8',  # 0.70 mg/m³ - Cyan-green transition
    '#3fd1c7',  # 0.85 mg/m³ - Light cyan
    '#5ac9c0',  # 1.00 mg/m³ - Light cyan
    '#7dd8c5',  # 1.15 mg/m³ - Pale cyan
    '#9de6c9',  # 1.30 mg/m³ - Pale cyan-green
    '#b8e0b8',  # 1.45 mg/m³ - Pale green
    '#c8e8a8',  # 1.55 mg/m³ - Green-yellow transition
    '#d4f0a8',  # 1.65 mg/m³ - Light green-yellow
    '#e0ec80',  # 1.70 mg/m³ - Green-yellow transition
    '#e8f080',  # 1.75 mg/m³ - Yellow-green
    '#F1C40F',  # 1.80 mg/m³ - Yellow
    '#e6b800',  # 1.95 mg/m³ - Yellow-orange
    '#D35400',  # 2.00 mg/m³ - Orange
]

SALINITY_COLORS = [
    '#0a0d3a', '#0d1f6d', '#12328f', '#1746b1',
    '#1f7bbf', '#22a6c5', '#27c8b8', '#3fdf9b',
    '#87f27a', '#c9f560', '#f7f060'
]

# Water clarity color scale - Deep blue to bright green
WATER_CLARITY_COLORS = [
    '#00204c', '#002b66', '#003780', '#00439a', '#004fb4',
    '#005bce', '#0067e8', '#0073ff', '#198eff', '#32a9ff',
    '#4bc4ff', '#64dfff', '#7dffff', '#7dffef', '#7dffdf',
    '#7dffcf', '#7dffbf', '#7dffaf', '#7dff9f', '#7dff8f',
    '#66ff66', '#4fff4f', '#38ff38', '#21ff21', '#0aff0a'
]

# Mixed Layer Depth - cool to warm progression with brightened professional tones
# Better contrast in shallow range while maintaining visual harmony
MLD_COLORS = [
    '#2d2d6b',  # brightened indigo (shallow MLD)
    '#1e4db8',  # brighter deep blue
    '#2196f3',  # bright blue
    '#03a9f4',  # light blue
    '#00bcd4',  # bright cyan
    '#009688',  # bright teal
    '#4caf50',  # bright green
    '#8bc34a',  # lime green
    '#cddc39',  # bright yellow-green
    '#ffc107',  # bright amber
    '#ff9800',  # bright orange
    '#f44336',  # bright red-orange (deep MLD)c
]

# Water Movement color scale - Deep blue to red gradient for SSH visualization
SSH_COLORS = [
    "#053061", "#0a3666", "#0f3d6c",
    "#B2E5F4", "#bae7f3", "#c1e9f2",
    "#c6dbef", "#cdddf0", "#d3dff1",
    "#d9e6f2", "#e0e9f3", "#e7ecf4",
    "#e5eef4", "#edf1f6", "#f0f5f7",
    "#f2f2f1", "#f3efeb", "#f5ebe6",
    "#f4e7df", "#f3e3d9", "#f3e0d4",
    "#f2d9c8", "#f1d1bc", "#f0c5ac",
    "#ecb399", "#e8a086", "#e48d73",
    "#dd7960", "#d66552", "#d15043",
    "#cb3e36", "#c52828", "#bf1f1f",
    "#b81717", "#b01010", "#a80808"
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
    sst_salty_vibes_colormap = create_continuous_colormap(SST_COLORS_SALTY_VIBES, 256)
    chlorophyll_colormap = create_continuous_colormap(CHLOROPHYLL_COLORS, 256)
    salinity_colormap = create_continuous_colormap(SALINITY_COLORS, 256)
    water_clarity_colormap = create_continuous_colormap(WATER_CLARITY_COLORS, 256)
    mld_colormap = create_continuous_colormap(MLD_COLORS, 256)
    ssh_colormap = create_continuous_colormap(SSH_COLORS, 256)

    # Register custom colormaps
    custom_colormaps = {
        "sst_high_contrast": sst_colormap,
        "sst_salty_vibes": sst_salty_vibes_colormap,
        "chlorophyll": chlorophyll_colormap,
        "salinity": salinity_colormap,
        "water_clarity": water_clarity_colormap,
        "mld_default": mld_colormap,
        "ssh": ssh_colormap
    }
    
    return custom_colormaps


def register_colormaps():
    """Register all colormaps with rio-tiler and return the dependency."""
    custom_colormaps = load_custom_colormaps()
    
    # Register the custom colormap with rio-tiler
    cmap = default_cmap.register(custom_colormaps)
    ColorMapParams = create_colormap_dependency(cmap)
    
    return ColorMapParams, cmap