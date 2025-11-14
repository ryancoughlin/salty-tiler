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
    # '#8B3A8B',  # 0.00 mg/m³ - Ultra-clear Gulf Stream (purple-pink)
    # '#6B238E',  # 0.01 mg/m³ - Transition
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

# Chlorophyll colormap optimized for log10 scaling - uses same exact colors as CHLOROPHYLL_COLORS
# Redistributed with more color stops in the lower range (0.01-0.1 mg/m³) to make them "pop" when log10 expanded
# Same exact color palette as CHLOROPHYLL_COLORS, just reorganized for log10 visualization
CHLOROPHYLL_LOG10_COLORS = [
    # All colors from CHLOROPHYLL_COLORS, redistributed with more emphasis on lower range
    '#4B1390',  # From CHLOROPHYLL_COLORS - Ultra-clear transition
    '#4B1390',  # Repeat for more stops in lower range
    '#2D1B69',  # From CHLOROPHYLL_COLORS - Clear waters start (indigo)
    '#2D1B69',  # Repeat
    '#1a1a4b',  # From CHLOROPHYLL_COLORS - Deep blue
    '#1a1a4b',  # Repeat
    '#0f2a6b',  # From CHLOROPHYLL_COLORS - Deep blue transition
    '#0f2a6b',  # Repeat
    '#0B3D91',  # From CHLOROPHYLL_COLORS - Medium blue
    '#0B3D91',  # Repeat
    '#0d5bb8',  # From CHLOROPHYLL_COLORS - Medium blue
    '#1464F4',  # From CHLOROPHYLL_COLORS - Bright blue
    '#1a71e1',  # From CHLOROPHYLL_COLORS - Blue-cyan transition start
    '#1e7ee8',  # From CHLOROPHYLL_COLORS - Blue-cyan
    '#2b8bc7',  # From CHLOROPHYLL_COLORS - Blue-cyan
    '#00B3B3',  # From CHLOROPHYLL_COLORS - Cyan
    '#26c4b8',  # From CHLOROPHYLL_COLORS - Cyan-green transition
    '#3fd1c7',  # From CHLOROPHYLL_COLORS - Light cyan
    '#5ac9c0',  # From CHLOROPHYLL_COLORS - Light cyan
    '#7dd8c5',  # From CHLOROPHYLL_COLORS - Pale cyan
    '#9de6c9',  # From CHLOROPHYLL_COLORS - Pale cyan-green
    '#b8e0b8',  # From CHLOROPHYLL_COLORS - Pale green
    '#c8e8a8',  # From CHLOROPHYLL_COLORS - Green-yellow transition
    '#d4f0a8',  # From CHLOROPHYLL_COLORS - Light green-yellow
    '#e0ec80',  # From CHLOROPHYLL_COLORS - Green-yellow transition
    '#e8f080',  # From CHLOROPHYLL_COLORS - Yellow-green
    '#F1C40F',  # From CHLOROPHYLL_COLORS - Yellow
    '#e6b800',  # From CHLOROPHYLL_COLORS - Yellow-orange
    '#D35400',  # From CHLOROPHYLL_COLORS - Orange
]

# Salinity color scale - Deep indigo/blue through cyan/teal to green to yellow
# Generic name: flow (smooth flowing transition from cool to warm)
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
# Generic name: cascade (bright vibrant cool-to-warm gradient)
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

# Bathymetry color scale - Professional deep indigo/blues to light blues for depth visualization
# Negative values (deeper) = darker indigos/blues, positive values (shallower) = lighter blues
# Professional marine-focused palette with clear contrast for shaded relief
# 
# Typical rescale ranges for shaded bathymetry (in meters):
# - Coastal/shelf regions: -500,0 or -1000,0
# - Regional ocean (e.g., Gulf of Maine, Northeast Canyons): -4000,0 or -3000,0
# - Deep ocean basins: -6000,0 or -8000,0
# - Custom regions: Check COG statistics or use /cog/statistics endpoint
#
# Example tile URL:
# /cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url={cog_url}&rescale=-4000,0&colormap_name=bathymetry
BATHYMETRY_COLORS = [
    # Deepest depths (deep indigo - professional, no purple)
    '#0a1a3a', '#0f1f3f', '#142444', '#1a2a4a', '#1f2f4f',
    '#243454', '#2a3a5a', '#2f3f5f', '#344464', '#394969',
    
    # Deep to medium depths (rich blues with good contrast)
    '#3e4e6e', '#445373', '#4a5878', '#505d7d', '#566282',
    '#5c6787', '#626c8c', '#687191', '#6e7696', '#747b9b',
    
    # Mid-depths (medium blues - clear contrast for shading detail)
    '#7a81a0', '#8087a5', '#868daa', '#8c93af', '#9299b4',
    '#989fb9', '#9ea5be', '#a4abc3', '#aab1c8', '#b0b7cd',
    
    # Transitional depths (brightening blues - maintains contrast)
    '#b6bdd2', '#bcc3d7', '#c2c9dc', '#c8cfe1', '#ced5e6',
    '#d4dbeb', '#dae1f0', '#e0e7f5', '#e6edfa', '#ecf3ff',
    
    # Shallow depths (light blues to cyan - distinct from deep)
    '#f2f8ff', '#f8feff', '#ffffff', '#f0f8ff', '#e6f5ff',
    '#dcf2ff', '#d2efff', '#c8ecff', '#bee9ff', '#b4e6ff',
    
    # Very shallow (pale blues - subtle transition)
    '#aae3ff', '#a0e0ff', '#96ddff', '#8cdaff', '#82d7ff',
    '#78d4ff', '#6ed1ff', '#64ceff', '#5acbff', '#50c8ff'
]



# Currents color scale - Light blue to red gradient for ocean current visualization
CURRENT_COLORS = [
    # Very slow/calm (0.0-0.1 knots) - light blue for bathymetry visibility
    '#e6f3ff', '#cce7ff', '#b3dbff',
    
    # Slow currents (0.1-0.5 knots) - light to medium blues
    '#99cfff', '#80c3ff', '#66b7ff',
    
    # Moderate currents (0.5-1.5 knots) - distinct blue to teal transition
    '#4dabff', '#339fff', '#1a93ff',
    
    # Strong currents (1.5-3.0 knots) - bright cyan to green transition
    '#00ced1', '#20b2aa', '#32cd32',
    
    # Very strong currents (3.0-5.0 knots) - green to yellow transition
    '#9acd32', '#ffd700', '#ffa500',
    
    # Extreme currents (5.0+ knots) - orange to red alerts
    '#ff6347', '#ff4500', '#dc143c', '#b22222'
]

# Boundary fire ramp - Threshold-focused with rapid color transition
# Emphasizes critical boundaries with sharp color shifts, fire-like intensity at boundaries
BOUNDARY_FIRE_COLORS = [
    '#8b008b',  # Dark purple
    '#b22222',  # Firebrick
    '#ff4500',  # Red-orange
    '#ff8c00',  # Dark orange
    '#ffd700',  # Gold
    '#adff2f',  # Green-yellow
    '#00bfff',  # Deep sky blue
    '#00008b',  # Dark blue
    '#191970'   # Midnight blue
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
    chlorophyll_log10_colormap = create_continuous_colormap(CHLOROPHYLL_LOG10_COLORS, 256)
    salinity_colormap = create_continuous_colormap(SALINITY_COLORS, 256)
    # Note: salinity_colormap is also registered as "flow" below for generic use
    water_clarity_colormap = create_continuous_colormap(WATER_CLARITY_COLORS, 256)
    mld_colormap = create_continuous_colormap(MLD_COLORS, 256)
    # Note: mld_colormap is also registered as "cascade" below for generic use
    ssh_colormap = create_continuous_colormap(SSH_COLORS, 256)
    currents_colormap = create_continuous_colormap(CURRENT_COLORS, 256)
    bathymetry_colormap = create_continuous_colormap(BATHYMETRY_COLORS, 256)
    boundary_fire_colormap = create_continuous_colormap(BOUNDARY_FIRE_COLORS, 256)

    # Register custom colormaps
    custom_colormaps = {
        "sst_high_contrast": sst_colormap,
        "sst_salty_vibes": sst_salty_vibes_colormap,
        "chlorophyll": chlorophyll_colormap,
        "chlorophyll_log10": chlorophyll_log10_colormap,  # Optimized for log10 scaling - emphasizes lower values
        "salinity": salinity_colormap,  # DEPRECATED: Use "flow" instead. Kept for backward compatibility.
        "flow": salinity_colormap,  # Generic dataset-agnostic name (smooth flowing transition from cool to warm)
        "water_clarity": water_clarity_colormap,
        "mld_default": mld_colormap,  # DEPRECATED: Use "cascade" instead. Kept for backward compatibility.
        "cascade": mld_colormap,  # Generic dataset-agnostic name (bright vibrant cool-to-warm gradient)
        "ssh": ssh_colormap,
        "currents": currents_colormap,
        "bathymetry": bathymetry_colormap,
        "boundary_fire": boundary_fire_colormap,
    }
    
    return custom_colormaps


def register_colormaps():
    """Register all colormaps with rio-tiler and return the dependency."""
    custom_colormaps = load_custom_colormaps()
    
    # Register the custom colormap with rio-tiler
    cmap = default_cmap.register(custom_colormaps)
    ColorMapParams = create_colormap_dependency(cmap)
    
    return ColorMapParams, cmap