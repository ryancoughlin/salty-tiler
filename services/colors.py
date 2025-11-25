#!/usr/bin/env python
"""
Color management service for ocean data visualization

This module handles all color scale registration and management for the TiTiler application,
including SST, chlorophyll, salinity, and water clarity color scales.
"""
import math
from typing import Dict, Tuple, List, Final
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

# Chlorophyll color scheme - exact Matplotlib specification with 39 color stops
# Colors positioned in log10 space for smooth transitions (0.01 to 8.0 mg/m³)
# Each color is paired with its chlorophyll value (mg/m³) for log10 positioning
CHLOROPHYLL_COLOR_STOPS = [
    # (chlorophyll_value_mg_per_m3, hex_color)
    (0.01, '#E040E0'),  # Ultra-clear Gulf Stream
    (0.02, '#9966CC'),  # Purple transition
    (0.03, '#6633CC'),  # Purple-blue blend
    (0.04, '#39299C'),  # Interpolated
    (0.05, '#0D1F6D'),  # Deep indigo blue
    (0.06, '#1759A9'),  # Interpolated
    (0.07, '#1E3A8A'),  # Deep blue
    (0.08, '#1E3D9C'),  # Interpolated
    (0.09, '#1E3FA5'),  # Interpolated
    (0.10, '#1E40AF'),  # Strong blue
    (0.15, '#1E68D9'),  # Interpolated
    (0.20, '#2196F3'),  # Professional blue
    (0.25, '#2D89F4'),  # Interpolated
    (0.30, '#3B82F6'),  # Light blue
    (0.35, '#4A9FE5'),  # Interpolated
    (0.40, '#59BCE5'),  # Interpolated
    (0.45, '#68D9D4'),  # Interpolated
    (0.50, '#00BCD4'),  # Cyan
    (0.60, '#00B4C8'),  # Interpolated
    (0.70, '#00ACC1'),  # Deeper cyan
    (0.80, '#007B9E'),  # Interpolated
    (0.90, '#005C7F'),  # Interpolated
    (1.00, '#00897B'),  # Teal-green
    (1.25, '#0F8A8D'),  # Interpolated
    (1.50, '#26A69A'),  # Teal
    (1.75, '#39B275'),  # Interpolated
    (2.00, '#4CAF50'),  # Green
    (2.50, '#59B85D'),  # Interpolated
    (3.00, '#66BB6A'),  # Bright green
    (3.50, '#7AC38F'),  # Interpolated
    (4.00, '#9CCC65'),  # Yellow-green
    (4.50, '#AED64F'),  # Interpolated
    (5.00, '#C0CA33'),  # Lime
    (5.50, '#DFE11A'),  # Interpolated
    (6.00, '#FDD835'),  # Yellow
    (6.50, '#FEC51A'),  # Interpolated
    (7.00, '#FFB300'),  # Amber-orange
    (7.50, '#FA9700'),  # Interpolated
    (8.00, '#F57C00'),  # Deep orange
]

# Extract just the colors for backward compatibility (used by other colormaps)
CHLOROPHYLL_COLORS = [color for _, color in CHLOROPHYLL_COLOR_STOPS]
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

# Magnitude colors - thermal/inferno style for front strength visualization
# Range: 0.0-0.25 per day (stretching rate)
# Generic name: magnitude (dataset-agnostic thermal/inferno gradient)
MAGNITUDE_COLORS: Final[List[str]] = [
    '#1a237e', '#283593', '#3949ab', '#5c6bc0',  # Deep indigo (very weak fronts)
    '#7986cb', '#9fa8da', '#c5cae9', '#e8eaf6',  # Light indigo to lavender
    '#f3e5f5', '#e1bee7', '#ce93d8', '#ba68c8',  # Purple transition
    '#ab47bc', '#9c27b0', '#8e24aa', '#7b1fa2',  # Purple to magenta
    '#6a1b9a', '#4a148c', '#3f51b5', '#2196f3',  # Deep purple to blue
    '#03a9f4', '#00bcd4', '#00acc1', '#0097a7',  # Cyan to teal
    '#00838f', '#006064', '#004d40', '#1b5e20',  # Dark teal to green
    '#2e7d32', '#388e3c', '#43a047', '#4caf50',  # Green transition
    '#66bb6a', '#81c784', '#a5d6a7', '#c8e6c9',  # Light green
    '#e8f5e8', '#fff3e0', '#ffe0b2', '#ffcc80',  # Light yellow
    '#ffb74d', '#ff9800', '#f57c00', '#ef6c00',  # Orange transition
    '#e65100', '#d84315', '#bf360c', '#a30000'   # Deep red (strong fronts)
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

def create_log10_positioned_colormap(
    value_color_pairs: List[Tuple[float, str]], 
    num_colors: int = 256,
    log_min: float = -2.0,
    log_max: float = 0.9030899869919435
) -> Dict[int, Tuple[int, int, int, int]]:
    """
    Create a colormap with colors positioned at their log10 values.
    
    Args:
        value_color_pairs: List of (chlorophyll_value_mg_per_m3, hex_color) tuples
        num_colors: Number of colors in output colormap (default 256)
        log_min: Minimum log10 value (default -2.0 = log10(0.01))
        log_max: Maximum log10 value (default 0.903 = log10(8.0))
    
    Returns:
        Dict mapping colormap index (0-255) to RGBA tuple
    """
    # Convert hex colors to RGB
    rgb_stops = [(val, hex_to_rgb(color)) for val, color in value_color_pairs]
    
    # Convert chlorophyll values to log10 and map to colormap indices
    log_range = log_max - log_min
    
    # Create mapping of colormap index to RGB color
    colormap = {}
    
    # Pre-compute log10 values for all stops and their exact indices
    log_stops = []
    stop_indices = {}  # Map exact stop indices to colors
    
    for val, rgb in rgb_stops:
        log_stop = math.log10(val) if val > 0 else log_min
        # Calculate exact index for this stop
        idx = int(((log_stop - log_min) / log_range) * (num_colors - 1))
        # Clamp to valid range
        idx = max(0, min(num_colors - 1, idx))
        log_stops.append((log_stop, rgb))
        stop_indices[idx] = rgb
    
    # For each colormap index, find which segment it falls in and interpolate
    for idx in range(num_colors):
        # If this is an exact stop index, use the exact color
        if idx in stop_indices:
            colormap[idx] = (*stop_indices[idx], 255)
            continue
        
        # Map index to log10 value
        log_val = log_min + (idx / (num_colors - 1)) * log_range
        
        # Find the two stops that bracket this log10 value
        for i in range(len(log_stops) - 1):
            log1, rgb1 = log_stops[i]
            log2, rgb2 = log_stops[i + 1]
            
            if log1 <= log_val <= log2:
                # Interpolate between the two colors
                if log2 == log1:
                    t = 0.0
                else:
                    t = (log_val - log1) / (log2 - log1)
                
                r = int(rgb1[0] * (1 - t) + rgb2[0] * t)
                g = int(rgb1[1] * (1 - t) + rgb2[1] * t)
                b = int(rgb1[2] * (1 - t) + rgb2[2] * t)
                
                colormap[idx] = (r, g, b, 255)
                break
        else:
            # Outside range - use closest stop
            if log_val < log_stops[0][0]:
                colormap[idx] = (*log_stops[0][1], 255)
            else:
                colormap[idx] = (*log_stops[-1][1], 255)
    
    return colormap

def load_custom_colormaps() -> Dict[str, Dict[int, Tuple[int, int, int, int]]]:
    """Load and register all custom colormaps."""
    # Generate the continuous colormaps
    sst_colormap = create_continuous_colormap(SST_COLORS_HIGH_CONTRAST, 256)
    sst_salty_vibes_colormap = create_continuous_colormap(SST_COLORS_SALTY_VIBES, 256)
    # Chlorophyll colormap positioned in log10 space to match Matplotlib
    chlorophyll_colormap = create_log10_positioned_colormap(CHLOROPHYLL_COLOR_STOPS, 256)
    salinity_colormap = create_continuous_colormap(SALINITY_COLORS, 256)
    # Note: salinity_colormap is also registered as "flow" below for generic use
    water_clarity_colormap = create_continuous_colormap(WATER_CLARITY_COLORS, 256)
    mld_colormap = create_continuous_colormap(MLD_COLORS, 256)
    # Note: mld_colormap is also registered as "cascade" below for generic use
    ssh_colormap = create_continuous_colormap(SSH_COLORS, 256)
    currents_colormap = create_continuous_colormap(CURRENT_COLORS, 256)
    bathymetry_colormap = create_continuous_colormap(BATHYMETRY_COLORS, 256)
    boundary_fire_colormap = create_continuous_colormap(BOUNDARY_FIRE_COLORS, 256)
    magnitude_colormap = create_continuous_colormap(MAGNITUDE_COLORS, 256)

    # Register custom colormaps
    custom_colormaps = {
        "sst_high_contrast": sst_colormap,
        "sst_salty_vibes": sst_salty_vibes_colormap,
        "chlorophyll": chlorophyll_colormap,
        "salinity": salinity_colormap,  # DEPRECATED: Use "flow" instead. Kept for backward compatibility.
        "flow": salinity_colormap,  # Generic dataset-agnostic name (smooth flowing transition from cool to warm)
        "water_clarity": water_clarity_colormap,
        "mld_default": mld_colormap,  # DEPRECATED: Use "cascade" instead. Kept for backward compatibility.
        "cascade": mld_colormap,  # Generic dataset-agnostic name (bright vibrant cool-to-warm gradient)
        "ssh": ssh_colormap,
        "currents": currents_colormap,
        "bathymetry": bathymetry_colormap,
        "boundary_fire": boundary_fire_colormap,
        "magnitude": magnitude_colormap,  # Generic dataset-agnostic name (thermal/inferno style gradient)
    }
    
    return custom_colormaps


def register_colormaps():
    """Register all colormaps with rio-tiler and return the dependency."""
    custom_colormaps = load_custom_colormaps()
    
    # Register the custom colormap with rio-tiler
    cmap = default_cmap.register(custom_colormaps)
    ColorMapParams = create_colormap_dependency(cmap)
    
    return ColorMapParams, cmap