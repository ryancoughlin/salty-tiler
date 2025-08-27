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

from typing import Final, Dict

# Chlorophyll color scale - Gulf Stream to productive shelf, explicit bounds
# Smooth chlorophyll colormap, 0–10 mg/m³, visually uniform, high resolution
CHLOROPHYLL_COLORS = [
    # 0.00–0.10: deep indigo to blue
    '#8B3A8B',  # 0.00
    '#7a3382',  # 0.01
    '#682c79',  # 0.02
    '#572570',  # 0.03
    '#461e67',  # 0.04
    '#35175e',  # 0.05
    '#241055',  # 0.06
    '#1a1a4b',  # 0.07
    '#15306a',  # 0.08
    '#0B3D91',  # 0.09
    '#0d5bb8',  # 0.10

    # 0.10–0.30: blue to blue-green
    '#1464F4',  # 0.12
    '#1e7ee8',  # 0.15
    '#2696e0',  # 0.18
    '#00B3B3',  # 0.20
    '#00a0a0',  # 0.25
    '#009090',  # 0.30

    # 0.30–1.00: blue-green to green
    '#3CB371',  # 0.35
    '#34a86a',  # 0.40
    '#2d8f5a',  # 0.50
    '#29984d',  # 0.60
    '#25a140',  # 0.70
    '#228B22',  # 1.00

    # 1.00–2.00: green to yellow-green
    '#2e9c1e',  # 1.20
    '#3aad1a',  # 1.40
    '#4a9c2a',  # 1.50
    '#7ebc1f',  # 1.70
    '#b1dc14',  # 1.90
    '#F1C40F',  # 2.00

    # 2.00–5.00: yellow to orange
    '#e6b800',  # 2.50
    '#e1a600',  # 3.00
    '#d98c00',  # 3.50
    '#D35400',  # 4.00
    '#c44500',  # 4.50
    '#b53600',  # 5.00

    # 5.00–10.00: orange to brownish-red
    '#a62a00',  # 5.50
    '#983000',  # 6.00
    '#8a3600',  # 6.50
    '#7c3c00',  # 7.00
    '#6e4200',  # 7.50
    '#605800',  # 8.00
    '#526e00',  # 8.50
    '#448400',  # 9.00
    '#369a00',  # 9.50
    '#28b000',  # 10.00
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
    '#f44336',  # bright red-orange (deep MLD)
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


def create_gamma_colormap(color_list: List[str], num_colors: int = 256, gamma: float = 0.5) -> Dict[int, Tuple[int, int, int, int]]:
    """Create a colormap with gamma bias toward low values ("fake log").

    When gamma < 1, this emphasizes the lower end of the scale by warping the
    interpolation parameter t -> t**gamma. This keeps linear rescale while
    visually allocating more contrast to smaller values.
    """
    rgb_colors = [hex_to_rgb(color) for color in color_list]
    num_segments = len(rgb_colors) - 1
    if num_segments <= 0:
        return {0: (*rgb_colors[0], 255)} if rgb_colors else {}

    cmap: Dict[int, Tuple[int, int, int, int]] = {}
    for idx in range(num_colors):
        t = idx / (num_colors - 1) if num_colors > 1 else 0.0
        s = t ** gamma
        pos = s * num_segments
        seg_index = min(int(pos), num_segments - 1)
        local_t = pos - seg_index

        r1, g1, b1 = rgb_colors[seg_index]
        r2, g2, b2 = rgb_colors[seg_index + 1]
        r = int(r1 * (1 - local_t) + r2 * local_t)
        g = int(g1 * (1 - local_t) + g2 * local_t)
        b = int(b1 * (1 - local_t) + b2 * local_t)
        cmap[idx] = (r, g, b, 255)

    return cmap


def load_custom_colormaps() -> Dict[str, Dict[int, Tuple[int, int, int, int]]]:
    """Load and register all custom colormaps."""
    # Generate the continuous colormaps
    sst_colormap = create_continuous_colormap(SST_COLORS_HIGH_CONTRAST, 256)
    sst_salty_vibes_colormap = create_continuous_colormap(SST_COLORS_SALTY_VIBES, 256)
    chlorophyll_colormap = create_continuous_colormap(CHLOROPHYLL_COLORS, 256)
    # Fake-log variants: stronger emphasis on lower ranges for fishing use-cases
    chlorophyll_low_focus = create_gamma_colormap(CHLOROPHYLL_COLORS, 256, gamma=0.5)
    chlorophyll_low_focus_strong = create_gamma_colormap(CHLOROPHYLL_COLORS, 256, gamma=0.30)
    salinity_colormap = create_continuous_colormap(SALINITY_COLORS, 256)
    water_clarity_colormap = create_continuous_colormap(WATER_CLARITY_COLORS, 256)
    mld_colormap = create_continuous_colormap(MLD_COLORS, 256)
    
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
        "sst_salty_vibes": sst_salty_vibes_colormap,
        "chlorophyll": chlorophyll_low_focus_strong,
        "chlorophyll_low_focus": chlorophyll_low_focus,
        "chlorophyll_low_focus_strong": chlorophyll_low_focus_strong,
        "salinity": salinity_colormap,
        "water_clarity": water_clarity_colormap,
        "mld_default": mld_colormap,
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