#!/usr/bin/env python
"""
Example of using custom configurations with convert_nc_to_cog.py
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from convert_nc_to_cog import (
    ProcessingConfig, 
    DatasetType, 
    save_config, 
    load_config, 
    process_file
)

def create_and_save_custom_config():
    """Create a custom configuration and save it to a file"""
    # Ensure the configs directory exists
    os.makedirs("configs", exist_ok=True)
    
    # Create a custom configuration for LEO data with higher quality resampling
    high_quality_config = ProcessingConfig(
        dataset_type=DatasetType.LEO,
        input_file="data/LEO-2025-05-01T000000Z.nc",
        output_file="data/LEO-2025-05-01T000000Z_highquality_cog.tif",
        subdataset="sea_surface_temperature",
        resample_method="cubic",  # Higher quality resampling
        compression="DEFLATE",
        predictor=3,  # Better for floating point data
        additional_options={
            "warp_dstnodata": "-9999",
            "cog_BLOCKSIZE": "512"
        }
    )
    
    # Save the configuration
    config_path = "configs/leo_high_quality.json"
    save_config(high_quality_config, config_path)
    print(f"Saved high quality configuration to {config_path}")
    
    return config_path

def load_and_use_config(config_path):
    """Load a configuration from a file and use it to process a NetCDF file"""
    # Load the configuration
    config = load_config(config_path)
    print(f"Loaded configuration: {config.dataset_type} - {config.input_file}")
    
    # Process the file with this configuration
    try:
        output_file = process_file(config)
        print(f"Successfully processed file: {output_file}")
    except Exception as e:
        print(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    # Create and save a custom configuration
    config_path = create_and_save_custom_config()
    
    # Load and use the configuration
    load_and_use_config(config_path) 