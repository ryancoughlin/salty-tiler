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