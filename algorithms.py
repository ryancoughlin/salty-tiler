#!/usr/bin/env python
"""
Custom algorithms for TiTiler processing

This module contains custom image processing algorithms that can be applied
to COG data before rescaling and colormapping.
"""
import numpy
from rio_tiler.models import ImageData
from titiler.core.algorithm.base import BaseAlgorithm


class OceanMask(BaseAlgorithm):
    """Make values outside specified range transparent.

    This algorithm marks pixels outside the specified min/max range as invalid,
    making them transparent in the final output. It's memory efficient because
    it only modifies the mask, not the data itself, allowing rescale to work
    properly with the original temperature values.

    Example usage:
        ?algorithm=ocean_mask&algorithm_params={"min_temp":15.0,"max_temp":25.0}
    """

    # Algorithm parameters
    min_temp: float = -10.0  # Minimum temperature to keep visible
    max_temp: float = 40.0   # Maximum temperature to keep visible

    # Metadata
    input_nbands: int = 1
    output_nbands: int = 1
    output_dtype: str = "float32"

    def __call__(self, img: ImageData) -> ImageData:
        """
        Mark out-of-range pixels as invalid.

        IMPORTANT: We only modify the mask, NOT the data.
        This keeps memory efficient and lets rescale work properly.
        """
        # Get existing mask if present (e.g., from NoData values in COG)
        existing_mask = img.array.mask if numpy.ma.is_masked(img.array) else False

        # Create mask for out-of-range temperatures
        # True = invalid (masked/transparent), False = valid (visible)
        temp_range_mask = (img.array < self.min_temp) | (img.array > self.max_temp)

        # Combine existing mask with temperature range mask
        # Pixel is masked if EITHER it was already masked OR outside temp range
        combined_mask = existing_mask | temp_range_mask

        # Create masked array - data stays intact, only mask changes
        masked_data = numpy.ma.MaskedArray(img.array, mask=combined_mask)

        return ImageData(
            masked_data,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=img.band_names,
            metadata=img.metadata,
            cutline_mask=img.cutline_mask,
        )


class ChlorophyllLog10RGB(BaseAlgorithm):
    """High-detail chlorophyll visualization using log10 space with continuous RGB output.

    Bypasses TiTiler's 256-color indexed colormap limitation by computing RGB values
    directly via vectorized interpolation in log10 space. This matches the quality
    of Matplotlib's LogNorm + 2048-step colormap rendering.

    Default range: 0.01-8.0 mg/m³ (log10: -2.0 to 0.903)
    Color stops: 19 scientifically-defined stops dense in the critical low range

    Usage (default range):
        /cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url={cog}&algorithm=chlorophyll_log10_rgb

    Usage (custom range):
        /cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url={cog}&algorithm=chlorophyll_log10_rgb&algorithm_params={"min_value":0.1,"max_value":5.0}

    No expression, rescale, or colormap_name needed - everything is handled internally.
    Values outside the min_value/max_value range are masked (transparent).
    """

    # Data range (mg/m³) - configurable via algorithm_params
    min_value: float = 0.01
    max_value: float = 8.0

    # 19 color stops from chlor_visualization.md - (chlorophyll_mg_m3, hex_color)
    # Dense in critical low range (0.01-1.0) for offshore fishing detail
    color_stops: list[tuple[float, str]] = [
        (0.01, '#E040E0'),  # Ultra-clear Gulf Stream
        (0.02, '#9966CC'),  # Purple transition
        (0.03, '#6633CC'),  # Purple-blue blend
        (0.05, '#0D1F6D'),  # Deep indigo (open ocean)
        (0.07, '#1E3A8A'),  # Deep blue
        (0.10, '#1E40AF'),  # Strong blue (oligotrophic)
        (0.20, '#2196F3'),  # Professional blue
        (0.30, '#3B82F6'),  # Light blue
        (0.50, '#00BCD4'),  # Cyan (transition)
        (0.70, '#00ACC1'),  # Deeper cyan
        (1.00, '#00897B'),  # Teal-green (offshore)
        (1.50, '#26A69A'),  # Teal (productive)
        (2.00, '#4CAF50'),  # Green (coastal)
        (3.00, '#66BB6A'),  # Bright green
        (4.00, '#9CCC65'),  # Yellow-green
        (5.00, '#C0CA33'),  # Lime
        (6.00, '#FDD835'),  # Yellow (blooms)
        (7.00, '#FFB300'),  # Amber-orange
        (8.00, '#F57C00'),  # Deep orange (max)
    ]

    # Metadata - outputs RGB image
    input_nbands: int = 1
    output_nbands: int = 3
    output_dtype: str = "uint8"

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )

    def __call__(self, img: ImageData) -> ImageData:
        """Apply log10 transformation and compute RGB via vectorized interpolation."""
        data = img.array[0]  # Single band input

        # Extract raw data and build combined mask (NoData + out-of-range)
        if numpy.ma.is_masked(data):
            raw_data = data.data
            nodata_mask = data.mask.copy()
        else:
            raw_data = data
            nodata_mask = numpy.isnan(raw_data)

        # Mask out-of-range values and combine with NoData mask
        out_of_range_mask = (raw_data < self.min_value) | (raw_data > self.max_value)
        combined_mask = nodata_mask | out_of_range_mask

        # Clamp to valid range for log10 processing
        clamped = numpy.clip(raw_data, self.min_value, self.max_value)

        # Compute log10 bounds dynamically from min_value/max_value
        log_min = numpy.log10(self.min_value)
        log_max = numpy.log10(self.max_value)
        log_range = log_max - log_min

        # Apply log10 transformation
        log_data = numpy.log10(clamped)

        # Normalize to 0-1 range in log10 space
        normalized = (log_data - log_min) / log_range

        # Build interpolation arrays: filter stops within range, add boundaries if needed
        log_positions = []
        r_values = []
        g_values = []
        b_values = []

        # Filter stops within range
        valid_stops = [(v, c) for v, c in self.color_stops if self.min_value <= v <= self.max_value]
        
        # Add boundary stops if range extends beyond color stops
        stops_to_process = []
        if not valid_stops or valid_stops[0][0] > self.min_value:
            stops_to_process.append((self.min_value, valid_stops[0][1] if valid_stops else self.color_stops[0][1]))
        stops_to_process.extend(valid_stops)
        if not valid_stops or valid_stops[-1][0] < self.max_value:
            stops_to_process.append((self.max_value, valid_stops[-1][1] if valid_stops else self.color_stops[-1][1]))

        # Convert to log10 positions and RGB arrays
        for chlor_val, hex_color in stops_to_process:
            log_pos = (numpy.log10(chlor_val) - log_min) / log_range
            log_positions.append(log_pos)
            r, g, b = self._hex_to_rgb(hex_color)
            r_values.append(r)
            g_values.append(g)
            b_values.append(b)

        log_positions = numpy.array(log_positions)
        r_values = numpy.array(r_values, dtype=numpy.float32)
        g_values = numpy.array(g_values, dtype=numpy.float32)
        b_values = numpy.array(b_values, dtype=numpy.float32)

        # Vectorized interpolation for each channel
        r_interp = numpy.interp(normalized.ravel(), log_positions, r_values).reshape(normalized.shape)
        g_interp = numpy.interp(normalized.ravel(), log_positions, g_values).reshape(normalized.shape)
        b_interp = numpy.interp(normalized.ravel(), log_positions, b_values).reshape(normalized.shape)

        # Create RGB output array
        rgb = numpy.stack([
            r_interp.astype(numpy.uint8),
            g_interp.astype(numpy.uint8),
            b_interp.astype(numpy.uint8),
        ], axis=0)

        # Create masked array for proper transparency
        # Broadcast 2D combined_mask (NoData + out-of-range) to all 3 RGB bands
        rgb_mask = numpy.broadcast_to(combined_mask, rgb.shape)
        rgb_masked = numpy.ma.MaskedArray(rgb, mask=rgb_mask)

        return ImageData(
            rgb_masked,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=['red', 'green', 'blue'],
            metadata=img.metadata,
            cutline_mask=img.cutline_mask,
        )