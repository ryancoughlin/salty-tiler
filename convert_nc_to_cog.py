#!/usr/bin/env python
"""
Convert NetCDF files to Cloud-Optimized GeoTIFF (COG)

This script extracts data from various NetCDF file formats (ABI-GOES19, LEO, etc.)
and converts them to Cloud-Optimized GeoTIFF (COG), preserving high resolution
and applying optional processing parameters.
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Literal, Tuple
from enum import Enum
from pydantic import BaseModel, Field


class DatasetType(str, Enum):
    """Supported NetCDF dataset types"""
    ABI_GOES19 = "abi_goes19"
    LEO = "leo"


class ProcessingConfig(BaseModel):
    """Base configuration for NetCDF processing"""
    dataset_type: DatasetType = Field(..., description="Type of NetCDF dataset")
    input_file: str = Field(..., description="Path to input NetCDF file")
    output_file: str = Field(..., description="Path to output COG file")
    subdataset: str = Field("sea_surface_temperature", description="NetCDF subdataset to extract")
    temp_file: Optional[str] = Field(None, description="Optional path for temporary file")
    bbox: Optional[str] = Field(None, description="Optional bounding box in format: xmin,ymin,xmax,ymax (if needed)")
    resample_method: str = Field("bilinear", description="Resampling method for gdalwarp")
    create_overviews: bool = Field(True, description="Whether to create overviews in the COG")
    compression: str = Field("DEFLATE", description="Compression method for the output COG")
    predictor: int = Field(2, description="Predictor value for compression")
    preserve_subset: bool = Field(True, description="Preserve the original subset area from NetCDF")
    additional_options: Dict[str, str] = Field(default_factory=dict, description="Additional GDAL options")
    
    def get_subdataset_path(self) -> str:
        """Get the full path to the specified NetCDF subdataset"""
        return f"NETCDF:\"{self.input_file}\":{self.subdataset}"
    
    def get_temp_file(self) -> str:
        """Get the temporary file path or generate one if not provided"""
        if not self.temp_file:
            return f"{os.path.splitext(self.output_file)[0]}_temp.tif"
        return self.temp_file


def get_netcdf_metadata(file_path: str) -> Dict:
    """
    Get metadata from a NetCDF file using gdalinfo
    
    Args:
        file_path: Path to the NetCDF file
        
    Returns:
        Dictionary containing metadata
    """
    cmd = ["gdalinfo", "-json", file_path]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        # Fall back to parsing the text output
        metadata = {}
        lines = result.stdout.split('\n')
        
        # Extract basic metadata
        for line in lines:
            if ':' in line and '=' in line:
                key, value = line.split('=', 1)
                metadata[key.strip()] = value.strip()
                
        return metadata


def get_dataset_bounds(file_path: str, dataset_type: DatasetType) -> Tuple[float, float, float, float]:
    """
    Get the actual bounds of the dataset from the NetCDF file
    
    Args:
        file_path: Path to the NetCDF file
        dataset_type: Type of dataset (ABI_GOES19, LEO, etc.)
        
    Returns:
        Tuple containing (xmin, ymin, xmax, ymax)
    """
    try:
        # Get bounds from file metadata
        cmd = ["ncdump", "-h", file_path]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # Parse ncdump output for global metadata
        bounds = {}
        for line in result.stdout.split('\n'):
            line = line.strip()
            if ':westernmost_longitude' in line:
                bounds['xmin'] = float(line.split('=')[1].strip(' ;f'))
            elif ':easternmost_longitude' in line:
                bounds['xmax'] = float(line.split('=')[1].strip(' ;f'))
            elif ':southernmost_latitude' in line:
                bounds['ymin'] = float(line.split('=')[1].strip(' ;f'))
            elif ':northernmost_latitude' in line:
                bounds['ymax'] = float(line.split('=')[1].strip(' ;f'))
                
        if len(bounds) == 4:
            return (bounds['xmin'], bounds['ymin'], bounds['xmax'], bounds['ymax'])
    except Exception as e:
        print(f"Warning: Could not extract bounds from NetCDF metadata: {str(e)}")
    
    # Fallback to GDAL to get the bounds
    subdataset_path = f"NETCDF:\"{file_path}\":sea_surface_temperature"
    cmd = ["gdalinfo", subdataset_path]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    
    # Parse output for corner coordinates
    corners = {}
    corner_section = False
    for line in result.stdout.split('\n'):
        if "Corner Coordinates:" in line:
            corner_section = True
            continue
        if corner_section:
            if "Upper Left" in line:
                parts = line.replace('(', ' ').replace(')', ' ').split()
                corners['xmin'] = float(parts[1])
                corners['ymax'] = float(parts[2])
            elif "Lower Right" in line:
                parts = line.replace('(', ' ').replace(')', ' ').split()
                corners['xmax'] = float(parts[1])
                corners['ymin'] = float(parts[2])
            elif "Center" in line:
                # End of corner section
                break
    
    if len(corners) == 4:
        return (corners['xmin'], corners['ymin'], corners['xmax'], corners['ymax'])
    
    # Last resort - use default extents for known dataset types
    if dataset_type == DatasetType.LEO:
        return (-85.0, 23.0, -77.0, 31.02)
    elif dataset_type == DatasetType.ABI_GOES19:
        return (-156.19, -81.15, 6.19, 81.15)
    
    # Return a global extent as last fallback
    return (-180.0, -90.0, 180.0, 90.0)


def convert_to_cog(config: ProcessingConfig) -> str:
    """
    Convert NetCDF subdataset to Cloud-Optimized GeoTIFF with optional parameters
    
    Args:
        config: Configuration for the conversion
    
    Returns:
        Path to the created COG file
    """
    # Setup file paths
    subdataset_path = config.get_subdataset_path()
    temp_file = config.get_temp_file()
    
    # Get dataset bounds if needed
    dataset_bounds = None
    if config.preserve_subset and not config.bbox:
        dataset_bounds = get_dataset_bounds(config.input_file, config.dataset_type)
        print(f"Detected dataset bounds: {dataset_bounds}")
    
    # Build gdalwarp command
    warp_cmd = [
        "gdalwarp",
        "-overwrite",
        "-of", "GTiff",
        "-r", config.resample_method,
        "-co", f"COMPRESS={config.compression}",
        "-co", f"PREDICTOR={config.predictor}",
        "-co", "BIGTIFF=YES",
    ]
    
    # Add bounds - either explicitly specified or detected from the dataset
    if config.bbox:
        warp_cmd.extend(["-te", *config.bbox.split(",")])
    elif dataset_bounds:
        warp_cmd.extend(["-te", str(dataset_bounds[0]), str(dataset_bounds[1]), 
                        str(dataset_bounds[2]), str(dataset_bounds[3])])
    
    # Preserve source SRS to ensure correct coordinate system
    warp_cmd.extend(["-s_srs", "EPSG:4326", "-t_srs", "EPSG:4326"])
    
    # Add any additional options
    for key, value in config.additional_options.items():
        if key.startswith("warp_"):
            option_name = key.replace("warp_", "")
            warp_cmd.extend([f"-{option_name}", value])
    
    # Add input and output files
    warp_cmd.extend([subdataset_path, temp_file])
    
    # Execute gdalwarp command
    print(f"Executing: {' '.join(warp_cmd)}")
    subprocess.run(warp_cmd, check=True)
    
    # Convert to COG
    cog_cmd = [
        "gdal_translate",
        "-of", "COG",
        "-co", f"COMPRESS={config.compression}",
        "-co", f"PREDICTOR={config.predictor}",
        "-co", "BIGTIFF=YES",
    ]
    
    # Add overview settings
    if config.create_overviews:
        cog_cmd.extend(["-co", "OVERVIEWS=IGNORE_EXISTING"])
    
    # Add any additional options
    for key, value in config.additional_options.items():
        if key.startswith("cog_"):
            option_name = key.replace("cog_", "")
            cog_cmd.extend([f"-co", f"{option_name}={value}"])
    
    cog_cmd.extend([temp_file, config.output_file])
    
    print(f"Executing: {' '.join(cog_cmd)}")
    subprocess.run(cog_cmd, check=True)
    
    # Clean up temporary file
    if os.path.exists(temp_file):
        os.remove(temp_file)
        
    return config.output_file


def get_default_configs() -> Dict[str, ProcessingConfig]:
    """
    Get default configurations for different dataset types
    
    Returns:
        Dictionary of default configurations by dataset type
    """
    return {
        DatasetType.ABI_GOES19: ProcessingConfig(
            dataset_type=DatasetType.ABI_GOES19,
            input_file="data/ABI-GOES19-GLOBAL-2025-04-26T170000Z.nc",
            output_file="data/ABI-GOES19-GLOBAL-2025-04-26T170000Z_SST_cog.tif",
            subdataset="sea_surface_temperature",
            resample_method="bilinear",
            preserve_subset=True,
            predictor=3  # Better for floating point data
        ),
        DatasetType.LEO: ProcessingConfig(
            dataset_type=DatasetType.LEO,
            input_file="data/LEO-2025-05-01T000000Z.nc",
            output_file="data/LEO-2025-05-01T000000Z_SST_cog.tif",
            subdataset="sea_surface_temperature",
            resample_method="bilinear",
            preserve_subset=True,
            predictor=3  # Better for floating point data
        )
    }


def process_file(config: ProcessingConfig) -> str:
    """
    Process a NetCDF file with the given configuration
    
    Args:
        config: Processing configuration
    
    Returns:
        Path to the created COG file
    """
    print(f"Processing {config.dataset_type} file: {config.input_file}")
    output_file = convert_to_cog(config)
    
    # Validate the output file
    print(f"Validating output file: {output_file}")
    validate_cmd = ["gdalinfo", output_file]
    subprocess.run(validate_cmd, check=True)
    
    return output_file


def batch_process(configs: List[ProcessingConfig]) -> List[str]:
    """
    Process multiple files with their respective configurations
    
    Args:
        configs: List of processing configurations
    
    Returns:
        List of created COG file paths
    """
    output_files = []
    for config in configs:
        try:
            output_file = process_file(config)
            output_files.append(output_file)
            print(f"Successfully created COG: {output_file}")
        except Exception as e:
            print(f"Error processing {config.input_file}: {str(e)}")
    
    return output_files


def save_config(config: ProcessingConfig, output_path: str) -> None:
    """
    Save a processing configuration to a JSON file
    
    Args:
        config: Processing configuration
        output_path: Path to save the configuration
    """
    with open(output_path, 'w') as f:
        f.write(config.json(indent=2))


def load_config(input_path: str) -> ProcessingConfig:
    """
    Load a processing configuration from a JSON file
    
    Args:
        input_path: Path to the configuration file
    
    Returns:
        Loaded processing configuration
    """
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    return ProcessingConfig(**data)


def main():
    """Main function to run the conversion process"""
    # Get default configurations
    configs = get_default_configs()
    
    # Example: Process all configured datasets
    batch_configs = list(configs.values())
    output_files = batch_process(batch_configs)
    
    print(f"Successfully processed {len(output_files)} files:")
    for output_file in output_files:
        print(f"  - {output_file}")


if __name__ == "__main__":
    main() 