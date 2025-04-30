#!/usr/bin/env python
"""
Convert ABI-GOES19-GLOBAL NetCDF to Cloud-Optimized GeoTIFF

This script extracts the sea_surface_temperature from the ABI-GOES19 NetCDF file
and converts it to a Cloud-Optimized GeoTIFF (COG), applying a bounding box with gdalwarp.
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional
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
    
    def get_subdataset_path(self) -> str:
        """Get the full path to the specified NetCDF subdataset"""
        return f"NETCDF:\"{self.input_file}\":{self.subdataset}"
    
    def get_temp_file(self) -> str:
        """Get the temporary file path or generate one if not provided"""
        if not self.temp_file:
            return f"{os.path.splitext(self.output_file)[0]}_temp.tif"
        return self.temp_file


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
    
    # Add bounding box if specified
    if config.bbox:
        warp_cmd.extend(["-te", *config.bbox.split(",")])
    
    # Add input and output files
    warp_cmd.extend([subdataset_path, temp_file])
    
    # Execute gdalwarp command
    print(f"Executing: {' '.join(warp_cmd)}")
    subprocess.run(warp_cmd, check=True)
    
    # Convert to COG
    cog_cmd = [
        "gdal_translate",
        "-of", "COG",
        "-co", "COMPRESS=DEFLATE",
        "-co", "PREDICTOR=2",
        "-co", "BIGTIFF=YES",
        "-co", "OVERVIEWS=IGNORE_EXISTING",
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
    # Configure the conversion
    config = ConversionConfig(
        input_file="data/ABI-GOES19-GLOBAL-2025-04-26T170000Z.nc",
        output_file="data/ABI-GOES19-GLOBAL-2025-04-26T170000Z_SST_cog.tif",
        # North America bounding box (approximate)
        bbox="-125,25,-66,49"
    )
    
    # Run the conversion
    output_file = convert_to_cog(config)
    print(f"Successfully created COG: {output_file}")
    
    # Validate the output file
    validate_cmd = ["gdalinfo", output_file]
    subprocess.run(validate_cmd, check=True)


if __name__ == "__main__":
    main() 