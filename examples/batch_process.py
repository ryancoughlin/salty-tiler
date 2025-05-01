#!/usr/bin/env python
"""
Example of batch processing multiple NetCDF files with convert_nc_to_cog.py
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from convert_nc_to_cog import (
    ProcessingConfig, 
    DatasetType, 
    batch_process
)

def batch_process_example():
    """Example of batch processing multiple files with different configurations"""
    # Create a list of configurations for different files
    configs = [
        # Standard ABI-GOES19 config
        ProcessingConfig(
            dataset_type=DatasetType.ABI_GOES19,
            input_file="data/ABI-GOES19-GLOBAL-2025-04-26T170000Z.nc",
            output_file="data/ABI-GOES19-GLOBAL-2025-04-26T170000Z_SST_standard_cog.tif",
            subdataset="sea_surface_temperature",
        ),
        
        # ABI-GOES19 with higher quality resampling
        ProcessingConfig(
            dataset_type=DatasetType.ABI_GOES19,
            input_file="data/ABI-GOES19-GLOBAL-2025-04-26T170000Z.nc",
            output_file="data/ABI-GOES19-GLOBAL-2025-04-26T170000Z_SST_highquality_cog.tif",
            subdataset="sea_surface_temperature",
            resample_method="cubic"
        ),
        
        # LEO with standard processing
        ProcessingConfig(
            dataset_type=DatasetType.LEO,
            input_file="data/LEO-2025-05-01T000000Z.nc",
            output_file="data/LEO-2025-05-01T000000Z_SST_standard_cog.tif",
            subdataset="sea_surface_temperature",
        ),
        
        # LEO with high-quality processing
        ProcessingConfig(
            dataset_type=DatasetType.LEO,
            input_file="data/LEO-2025-05-01T000000Z.nc",
            output_file="data/LEO-2025-05-01T000000Z_SST_highquality_cog.tif",
            subdataset="sea_surface_temperature",
            resample_method="cubic",
            predictor=3,
            additional_options={
                "warp_dstnodata": "-9999",
                "cog_BLOCKSIZE": "512"
            }
        )
    ]
    
    # Process all files in batch
    output_files = batch_process(configs)
    
    # Print results
    print(f"\nProcessing complete. Generated {len(output_files)} files:")
    for output_file in output_files:
        print(f"  - {output_file}")

if __name__ == "__main__":
    batch_process_example() 