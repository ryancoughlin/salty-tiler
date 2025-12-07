#!/usr/bin/env python
"""
Custom algorithms for TiTiler processing

This module contains custom image processing algorithms that can be applied
to COG data before rescaling and colormapping.
"""
import numpy
from rio_tiler.models import ImageData
from titiler.core.algorithm.base import BaseAlgorithm


class Log10(BaseAlgorithm):
    """Apply log10 transformation to image data.
    
    Simple log10 transformation for data with wide dynamic ranges.
    Uses numpy.ma (masked arrays) to properly handle NoData.
    """
    
    # Algorithm parameters
    eps: float = 1e-6  # Small value to avoid log(0)
    
    # Metadata (required by BaseAlgorithm)
    input_nbands: int = 1
    output_nbands: int = 1 
    output_dtype: str = "float32"
    
    def __call__(self, img: ImageData) -> ImageData:
        """Apply log10 transformation to image data."""
        # Use img.array (masked array) and numpy.ma functions like TiTiler does
        transformed_array = numpy.ma.log10(numpy.ma.clip(img.array, self.eps, None))
        
        return ImageData(
            transformed_array,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=img.band_names,
            metadata=img.metadata,
            cutline_mask=img.cutline_mask,
        )


class Log10Chlorophyll(BaseAlgorithm):
    """Specialized log10 transformation for chlorophyll data with clamping.

    Clamps chlorophyll values to 0-2 mg/m³ range for realistic ocean visualization,
    then applies log10 transformation. Optimized for coastal and Gulf Stream waters.
    Uses numpy.ma (masked arrays) to properly handle NoData.
    """

    # Algorithm parameters optimized for 0-2 mg/m³ chlorophyll range
    eps: float = 0.0001  # Small value to avoid log(0), suitable for 0-2 range
    max_value: float = 2.0  # Maximum chlorophyll value (mg/m³)

    # Metadata
    input_nbands: int = 1
    output_nbands: int = 1
    output_dtype: str = "float32"

    def __call__(self, img: ImageData) -> ImageData:
        """Apply clamping and log10 transformation for chlorophyll data."""
        # First clamp values to 0-2 mg/m³ range, then apply eps for log safety
        clamped_array = numpy.ma.clip(img.array, self.eps, self.max_value)
        # Use img.array (masked array) and numpy.ma functions like TiTiler does
        transformed_array = numpy.ma.log10(clamped_array)

        return ImageData(
            transformed_array,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=img.band_names,
            metadata=img.metadata,
            cutline_mask=img.cutline_mask,
        )


class SqrtChlorophyll(BaseAlgorithm):
    """Square root transformation for chlorophyll data with clamping.

    Clamps chlorophyll values to 0-2 mg/m³ range, then applies square root transformation.
    This provides gentler scaling than log10, emphasizing lower values for better
    watercolor transitions while maintaining detail across the full range.
    """

    # Algorithm parameters
    max_value: float = 2.0  # Maximum chlorophyll value (mg/m³)

    # Metadata
    input_nbands: int = 1
    output_nbands: int = 1
    output_dtype: str = "float32"

    def __call__(self, img: ImageData) -> ImageData:
        """Apply clamping and square root transformation for chlorophyll data."""
        # Clamp values to 0-2 mg/m³ range
        clamped_array = numpy.ma.clip(img.array, 0.0, self.max_value)
        # Apply square root transformation
        transformed_array = numpy.ma.sqrt(clamped_array)

        return ImageData(
            transformed_array,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=img.band_names,
            metadata=img.metadata,
            cutline_mask=img.cutline_mask,
        )


class GammaChlorophyll(BaseAlgorithm):
    """Gamma correction for chlorophyll data with clamping.

    Clamps chlorophyll values to 0-2 mg/m³ range, then applies gamma correction (power < 1).
    This emphasizes lower values for better watercolor transitions.
    Gamma = 0.5 provides strong emphasis on low values, gamma = 0.7 is more moderate.
    """

    # Algorithm parameters
    max_value: float = 2.0  # Maximum chlorophyll value (mg/m³)
    gamma: float = 0.6      # Gamma value (< 1 emphasizes low values)

    # Metadata
    input_nbands: int = 1
    output_nbands: int = 1
    output_dtype: str = "float32"

    def __call__(self, img: ImageData) -> ImageData:
        """Apply clamping and gamma correction for chlorophyll data."""
        # Clamp values to 0-2 mg/m³ range
        clamped_array = numpy.ma.clip(img.array, 0.0, self.max_value)
        # Apply gamma correction (emphasizes low values when gamma < 1)
        transformed_array = numpy.ma.power(clamped_array, self.gamma)

        return ImageData(
            transformed_array,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=img.band_names,
            metadata=img.metadata,
            cutline_mask=img.cutline_mask,
        )


class LinearChlorophyll(BaseAlgorithm):
    """Linear scaling for chlorophyll data with clamping.

    Clamps chlorophyll values to 0-2 mg/m³ range with no transformation.
    Provides equal emphasis across all values - good for direct interpretation.
    """

    # Algorithm parameters
    max_value: float = 2.0  # Maximum chlorophyll value (mg/m³)

    # Metadata
    input_nbands: int = 1
    output_nbands: int = 1
    output_dtype: str = "float32"

    def __call__(self, img: ImageData) -> ImageData:
        """Apply clamping only (no transformation) for chlorophyll data."""
        # Clamp values to 0-2 mg/m³ range
        transformed_array = numpy.ma.clip(img.array, 0.0, self.max_value)

        return ImageData(
            transformed_array,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=img.band_names,
            metadata=img.metadata,
            cutline_mask=img.cutline_mask,
        )


class ChlorophyllRangeMapper(BaseAlgorithm):
    """Custom chlorophyll color mapping algorithm with specific concentration ranges.

    Maps chlorophyll concentrations to colors based on scientifically defined ranges:
    - 0.00-0.05: Purple water (ultra-clear Gulf Stream)
    - 0.05-0.10: Deep Blue water (offshore conditions)
    - 0.10-0.30: Blue to Light Blue (transition zones)
    - 0.30-1.00: Light Green to Green (shelf waters)
    - 1.00-2.00: Yellow to Orange (productive waters)

    Uses continuous gradient mapping with smooth interpolation between ranges.
    """

    # Algorithm parameters
    max_value: float = 2.0  # Maximum chlorophyll value (mg/m³)

    # Define chlorophyll concentration breakpoints and corresponding RGB colors
    breakpoints: list[float] = [0.0, 0.05, 0.10, 0.30, 1.00, 2.00]
    colors_rgb: list[list[int]] = [
        [139, 58, 139],    # #8B3A8B - Purple water (0.00-0.05)
        [26, 26, 75],      # #1A1A4B - Deep Blue water (0.05-0.10)
        [13, 91, 184],     # #0D5BB8 - Blue (0.10-0.30)
        [30, 126, 232],    # #1E7EE8 - Blue to cyan (0.30-1.00)
        [241, 196, 15],    # #F1C40F - Yellow (1.00-2.00)
        [211, 84, 0]       # #D35400 - Orange-brown (2.00+)
    ]

    # Metadata - outputs RGB image
    input_nbands: int = 1
    output_nbands: int = 3
    output_dtype: str = "uint8"

    def __call__(self, img: ImageData) -> ImageData:
        """Map chlorophyll concentrations to RGB colors based on defined ranges."""
        data = img.array[0]  # Single band input

        # Create RGB output array
        height, width = data.shape
        rgb = numpy.zeros((3, height, width), dtype=numpy.uint8)

        # Identify NoData/NaN pixels BEFORE any processing
        nodata_mask = None

        # Check for NaN values in the data
        if numpy.ma.is_masked(data):
            # Handle masked arrays
            nodata_mask = data.mask
            data_valid = data.data  # Get underlying data
        else:
            # Check for NaN values manually
            nodata_mask = numpy.isnan(data)

        # Also check for the image's built-in mask if it exists
        if hasattr(img, 'mask') and img.mask is not None:
            if nodata_mask is None:
                nodata_mask = img.mask[0]
            else:
                nodata_mask = nodata_mask | img.mask[0]

        # Clamp only valid data to the range
        data_clamped = numpy.ma.clip(data, 0.0, self.max_value)

        # Map each concentration range to its color (only for valid pixels)
        for i in range(len(self.breakpoints) - 1):
            min_val = self.breakpoints[i]
            max_val = self.breakpoints[i + 1]
            color_rgb = self.colors_rgb[i]

            # Find pixels in this range AND not NoData
            if nodata_mask is not None:
                mask = ((data_clamped >= min_val) & (data_clamped < max_val) & ~nodata_mask)
            else:
                mask = (data_clamped >= min_val) & (data_clamped < max_val)

            # Apply color to all channels
            for channel in range(3):
                rgb[channel, mask] = color_rgb[channel]

        # Handle the maximum value (only for valid pixels)
        if nodata_mask is not None:
            max_mask = (data_clamped >= self.breakpoints[-1]) & ~nodata_mask
        else:
            max_mask = (data_clamped >= self.breakpoints[-1])

        for channel in range(3):
            rgb[channel, max_mask] = self.colors_rgb[-1][channel]

        # Create masked array for proper transparency
        if nodata_mask is not None:
            rgb_mask = numpy.broadcast_to(nodata_mask, rgb.shape)
            rgb_masked = numpy.ma.MaskedArray(rgb, mask=rgb_mask)
        else:
            rgb_masked = rgb

        return ImageData(
            rgb_masked,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=['red', 'green', 'blue'],
            metadata=img.metadata,
            cutline_mask=img.cutline_mask,
        )


class ChlorophyllSmoothMapper(BaseAlgorithm):
    """Smooth continuous chlorophyll color mapping with interpolation.

    Uses linear interpolation between defined concentration points to create
    smooth color transitions. Based on the user's color scale but with
    continuous blending rather than discrete ranges.
    """

    # Algorithm parameters
    max_value: float = 2.0  # Maximum chlorophyll value (mg/m³)

    # Define key concentration points and their colors for interpolation
    conc_points: list[float] = [0.0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 0.75, 1.00, 1.50, 2.00]
    colors_rgb: list[list[int]] = [
        [139, 58, 139],    # #8B3A8B - 0.00 mg/m³
        [26, 26, 75],      # #1A1A4B - 0.02 mg/m³
        [11, 61, 145],     # #0B3D91 - 0.05 mg/m³
        [13, 91, 184],     # #0D5BB8 - 0.10 mg/m³
        [20, 70, 244],     # #1464F4 - 0.20 mg/m³
        [30, 126, 232],    # #1E7EE8 - 0.35 mg/m³
        [0, 179, 179],     # #00B3B3 - 0.50 mg/m³
        [63, 209, 199],    # #3FD1C7 - 0.75 mg/m³
        [241, 196, 15],    # #F1C40F - 1.00 mg/m³
        [230, 184, 0],     # #E6B800 - 1.50 mg/m³
        [211, 84, 0]       # #D35400 - 2.00 mg/m³
    ]

    # Metadata - outputs RGB image
    input_nbands: int = 1
    output_nbands: int = 3
    output_dtype: str = "uint8"

    def _interpolate_color(self, value: float) -> list:
        """Interpolate color for a given chlorophyll concentration."""
        # Handle values outside range
        if value <= self.conc_points[0]:
            return self.colors_rgb[0]
        if value >= self.conc_points[-1]:
            return self.colors_rgb[-1]

        # Find the two closest points for interpolation
        for i in range(len(self.conc_points) - 1):
            if self.conc_points[i] <= value <= self.conc_points[i + 1]:
                # Linear interpolation between the two colors
                t = (value - self.conc_points[i]) / (self.conc_points[i + 1] - self.conc_points[i])

                r = int(self.colors_rgb[i][0] + t * (self.colors_rgb[i + 1][0] - self.colors_rgb[i][0]))
                g = int(self.colors_rgb[i][1] + t * (self.colors_rgb[i + 1][1] - self.colors_rgb[i][1]))
                b = int(self.colors_rgb[i][2] + t * (self.colors_rgb[i + 1][2] - self.colors_rgb[i][2]))

                return [r, g, b]

        return self.colors_rgb[-1]  # Fallback

    def __call__(self, img: ImageData) -> ImageData:
        """Map chlorophyll concentrations to RGB colors with smooth interpolation."""
        data = img.array[0]  # Single band input

        # Create RGB output array
        height, width = data.shape
        rgb = numpy.zeros((3, height, width), dtype=numpy.uint8)

        # Identify NoData/NaN pixels BEFORE any processing
        nodata_mask = None

        # Check for NaN values in the data
        if numpy.ma.is_masked(data):
            # Handle masked arrays
            nodata_mask = data.mask
        else:
            # Check for NaN values manually
            nodata_mask = numpy.isnan(data)

        # Also check for the image's built-in mask if it exists
        if hasattr(img, 'mask') and img.mask is not None:
            if nodata_mask is None:
                nodata_mask = img.mask[0]
            else:
                nodata_mask = nodata_mask | img.mask[0]

        # Clamp only valid data to the range
        data_clamped = numpy.ma.clip(data, 0.0, self.max_value)

        # Apply color interpolation to each pixel (only for valid pixels)
        for i in range(height):
            for j in range(width):
                # Skip NoData pixels
                if nodata_mask is not None and nodata_mask[i, j]:
                    continue

                if not numpy.ma.is_masked(data_clamped[i, j]):
                    color_rgb = self._interpolate_color(float(data_clamped[i, j]))
                    for channel in range(3):
                        rgb[channel, i, j] = color_rgb[channel]

        # Create masked array for proper transparency
        if nodata_mask is not None:
            rgb_mask = numpy.broadcast_to(nodata_mask, rgb.shape)
            rgb_masked = numpy.ma.MaskedArray(rgb, mask=rgb_mask)
        else:
            rgb_masked = rgb

        return ImageData(
            rgb_masked,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=['red', 'green', 'blue'],
            metadata=img.metadata,
            cutline_mask=img.cutline_mask,
        )


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

    Range: 0.01-8.0 mg/m³ (log10: -2.0 to 0.903)
    Color stops: 19 scientifically-defined stops dense in the critical low range

    Usage:
        /cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url={cog}&algorithm=chlorophyll_log10_rgb

    No expression, rescale, or colormap_name needed - everything is handled internally.
    """

    # Data range (mg/m³)
    min_value: float = 0.01
    max_value: float = 8.0

    # Log10 range bounds
    log_min: float = -2.0  # log10(0.01)
    log_max: float = 0.9030899869919435  # log10(8.0)

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

        # Build NoData mask
        if numpy.ma.is_masked(data):
            nodata_mask = data.mask.copy()
        else:
            nodata_mask = numpy.isnan(data)

        # Clamp to valid range
        clamped = numpy.clip(data.data if numpy.ma.is_masked(data) else data, self.min_value, self.max_value)

        # Apply log10 transformation
        log_data = numpy.log10(clamped)

        # Normalize to 0-1 range in log10 space
        log_range = self.log_max - self.log_min
        normalized = (log_data - self.log_min) / log_range

        # Pre-compute log10 positions and RGB values for interpolation
        log_positions = []
        r_values = []
        g_values = []
        b_values = []

        for chlor_val, hex_color in self.color_stops:
            log_pos = (numpy.log10(chlor_val) - self.log_min) / log_range
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
        # Broadcast 2D nodata_mask to all 3 RGB bands
        rgb_mask = numpy.broadcast_to(nodata_mask, rgb.shape)
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


class MixedLayerDepthGradient(BaseAlgorithm):
    """Calculate spatial gradient magnitude of mixed layer depth (MLD) data.
    
    Computes the spatial gradient of MLD values to identify areas where the
    mixed layer depth changes rapidly. Strong gradients indicate thermocline
    breaks and productive fishing zones where ocean fronts occur.
    
    The gradient magnitude is calculated as: sqrt((∂MLD/∂x)² + (∂MLD/∂y)²)
    where x and y are spatial coordinates.
    
    Uses Sobel operator (default) for better edge detection, or numpy.gradient
    for simpler finite difference calculation.
    
    Usage:
        /cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url={mld_cog_url}&algorithm=mld_gradient&rescale={min},{max}
    
    Example:
        ?algorithm=mld_gradient&algorithm_params={"method":"sobel"}
        ?algorithm=mld_gradient&algorithm_params={"method":"numpy","output_direction":true}
    """
    
    # Algorithm parameters
    method: str = "sobel"  # "sobel" or "numpy" for gradient calculation
    output_direction: bool = False  # If True, output 2 bands (magnitude, direction)
    
    # Metadata
    input_nbands: int = 1
    output_nbands: int = 1  # Will be 2 if output_direction=True
    output_dtype: str = "float32"
    
    def __call__(self, img: ImageData) -> ImageData:
        """Calculate spatial gradient magnitude (and optionally direction) of MLD data."""
        data = img.array[0]  # Single band input
        
        # Extract data and mask
        if numpy.ma.is_masked(data):
            nodata_mask = data.mask.copy()
            data_array = data.data.copy()
        else:
            nodata_mask = numpy.isnan(data)
            data_array = data.copy()
        
        # Fill masked/NaN values with 0 for gradient calculation
        # We'll mask them back out later
        data_filled = numpy.where(nodata_mask, 0.0, data_array)
        
        # Calculate gradient components
        if self.method == "sobel":
            # Sobel operator provides better edge detection
            # Returns gradients in x and y directions
            grad_x = ndimage.sobel(data_filled, axis=1)  # Horizontal gradient (x-direction)
            grad_y = ndimage.sobel(data_filled, axis=0)  # Vertical gradient (y-direction)
        else:  # method == "numpy"
            # numpy.gradient returns gradients along each axis
            grad_y, grad_x = numpy.gradient(data_filled)
        
        # Calculate gradient magnitude: sqrt(dx² + dy²)
        magnitude = numpy.sqrt(grad_x**2 + grad_y**2)
        
        # Mask out NoData pixels in the result
        magnitude = numpy.ma.masked_array(magnitude, mask=nodata_mask)
        
        # Prepare output
        if self.output_direction:
            # Calculate direction: atan2(dy, dx) in degrees (0-360)
            direction = numpy.degrees(numpy.arctan2(grad_y, grad_x))
            # Convert to 0-360 range (atan2 returns -180 to 180)
            direction = numpy.where(direction < 0, direction + 360, direction)
            direction = numpy.ma.masked_array(direction, mask=nodata_mask)
            
            # Stack magnitude and direction as 2-band output
            output_array = numpy.ma.stack([magnitude, direction], axis=0)
            band_names = ['gradient_magnitude', 'gradient_direction']
            output_nbands = 2
        else:
            # Single band output (magnitude only)
            output_array = magnitude[numpy.newaxis, :, :]  # Add band dimension
            band_names = ['gradient_magnitude']
            output_nbands = 1
        
        return ImageData(
            output_array,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=band_names,
            metadata=img.metadata,
            cutline_mask=img.cutline_mask,
        )