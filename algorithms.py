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

        # Handle NoData values (set to transparent/black)
        if nodata_mask is not None:
            for channel in range(3):
                rgb[channel, nodata_mask] = 0

        return ImageData(
            rgb,
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

        return ImageData(
            rgb,
            assets=img.assets,
            crs=img.crs,
            bounds=img.bounds,
            band_names=['red', 'green', 'blue'],
            metadata=img.metadata,
            cutline_mask=img.cutline_mask,
        )