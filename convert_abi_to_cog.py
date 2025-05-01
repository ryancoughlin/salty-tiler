#!/usr/bin/env python
"""
Convert ABI-GOES19-GLOBAL NetCDF to Cloud-Optimized GeoTIFF

This script extracts the sea_surface_temperature from the ABI-GOES19 NetCDF file
and converts it to a Cloud-Optimized GeoTIFF (COG), applying a bounding box with gdalwarp.
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, List, Union
from pydantic import BaseModel, Field


class ConversionConfig(BaseModel):
    """Configuration for NetCDF to COG conversion with bounding box"""
    input_file: str = Field(..., description="Path to input NetCDF file")
    output_file: str = Field(..., description="Path to output COG file")
    subdataset: str = Field("sea_surface_temperature", description="NetCDF subdataset to extract")
    temp_file: Optional[str] = Field(None, description="Optional path for temporary file")
    bbox: Optional[str] = Field(None, description="Bounding box in format: xmin,ymin,xmax,ymax")
    resample_method: str = Field("bilinear", description="Resampling method for gdalwarp")
    output_format: str = Field("COG", description="Output format")
    # New parameter for target resolution (in degrees for geographic data)
    target_resolution: Optional[float] = Field(None, description="Target resolution in degrees (e.g., 0.001 ≈ 100m)")
    # New parameter for maximum zoom level
    max_zoom_level: int = Field(14, description="Maximum zoom level for the COG")
    # New parameter for internal tile size
    tile_size: int = Field(512, description="Internal tile size for the COG")
    
    def get_subdataset_path(self) -> str:
        """Get the full path to the specified NetCDF subdataset"""
        return f"NETCDF:\"{self.input_file}\":{self.subdataset}"
    
    def get_temp_file(self) -> str:
        """Get the temporary file path or generate one if not provided"""
        if not self.temp_file:
            return f"{os.path.splitext(self.output_file)[0]}_temp.tif"
        return self.temp_file


def get_dataset_info(filepath: str, subdataset: Optional[str] = None) -> Dict:
    """
    Get information about the dataset using gdalinfo
    
    Args:
        filepath: Path to the dataset
        subdataset: Optional subdataset name
        
    Returns:
        Dictionary with dataset information
    """
    dataset_path = filepath
    if subdataset:
        dataset_path = f"NETCDF:\"{filepath}\":{subdataset}"
    
    cmd = ["gdalinfo", "-json", dataset_path]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    
    # Parse JSON output
    import json
    return json.loads(result.stdout)


def convert_to_cog(config: ConversionConfig) -> str:
    """
    Convert NetCDF subdataset to Cloud-Optimized GeoTIFF with optional bounding box
    
    Args:
        config: Configuration for the conversion
    
    Returns:
        Path to the created COG file
    """
    # Setup file paths
    subdataset_path = config.get_subdataset_path()
    temp_file = config.get_temp_file()
    
    # Get dataset info to determine appropriate resolution if not specified
    if not config.target_resolution:
        dataset_info = get_dataset_info(config.input_file, config.subdataset)
        # Try to get pixel size from the dataset
        if "geoTransform" in dataset_info:
            # For projected data
            pixel_width = abs(dataset_info["geoTransform"][1])
            pixel_height = abs(dataset_info["geoTransform"][5])
            config.target_resolution = min(pixel_width, pixel_height) / 2  # Use half the original resolution
        else:
            # Default to a reasonably high resolution if we can't determine
            config.target_resolution = 0.001  # ~100m at equator
    
    # Build gdalwarp command
    warp_cmd = [
        "gdalwarp",
        "-overwrite",
        "-of", "GTiff",
        "-r", config.resample_method,
        "-co", "COMPRESS=DEFLATE",
        "-co", "PREDICTOR=2",
        "-co", "BIGTIFF=YES",
    ]
    
    # Add target resolution
    warp_cmd.extend(["-tr", str(config.target_resolution), str(config.target_resolution)])
    
    # Add bounding box if specified
    if config.bbox:
        warp_cmd.extend(["-te", *config.bbox.split(",")])
    
    # Set output data type to preserve precision
    warp_cmd.extend(["-ot", "Float32"])
    
    # Add input and output files
    warp_cmd.extend([subdataset_path, temp_file])
    
    # Execute gdalwarp command
    print(f"Executing: {' '.join(warp_cmd)}")
    subprocess.run(warp_cmd, check=True)
    
    # Calculate appropriate overview levels
    overview_levels = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048]
    
    # Convert to COG with proper overviews
    cog_cmd = [
        "gdal_translate",
        "-of", "COG",
        "-co", "COMPRESS=DEFLATE",
        "-co", "PREDICTOR=2",
        "-co", "BIGTIFF=YES",
        "-co", f"BLOCKSIZE={config.tile_size}",
        "-co", f"OVERVIEW_RESAMPLING={config.resample_method}",
        "-co", f"RESAMPLING={config.resample_method}",
        "-co", f"OVERVIEWS=AUTO",
        "-co", f"MAX_ZOOM_LEVEL={config.max_zoom_level}",
        temp_file,
        config.output_file
    ]
    
    print(f"Executing: {' '.join(cog_cmd)}")
    subprocess.run(cog_cmd, check=True)
    
    # Clean up temporary file
    if os.path.exists(temp_file):
        os.remove(temp_file)
        
    return config.output_file


def main():
    """Main function to run the conversion process"""
    # Configure the conversion for ABI-GOES19
    abi_config = ConversionConfig(
        input_file="data/ABI-GOES19-GLOBAL-2025-04-26T170000Z.nc",
        output_file="data/ABI-GOES19-GLOBAL-2025-04-26T170000Z_SST_cog.tif",
        # North America bounding box (approximate)
        bbox="-125,25,-66,49",
        target_resolution=0.01,  # ~1km at equator
        max_zoom_level=12
    )
    
    # Run the conversion
    output_file = convert_to_cog(abi_config)
    print(f"Successfully created ABI-GOES19 COG: {output_file}")
    
    # Configure the conversion for LEO dataset
    leo_config = ConversionConfig(
        input_file="data/LEO-2025-05-01T000000Z.nc",
        output_file="data/LEO-2025-05-01T000000Z_SST_cog.tif",
        # Florida region (approximate)
        bbox="-85,23,-77,31.02",
        target_resolution=0.002,  # ~200m at equator - higher resolution for LEO
        max_zoom_level=14  # More zoom levels for LEO's higher resolution
    )
    
    # Run the conversion for LEO
    leo_output_file = convert_to_cog(leo_config)
    print(f"Successfully created LEO COG: {leo_output_file}")
    
    # Validate the output files
    for file in [output_file, leo_output_file]:
        print(f"\nValidating {file}:")
        validate_cmd = ["gdalinfo", file]
        subprocess.run(validate_cmd, check=True)


if __name__ == "__main__":
    main() 