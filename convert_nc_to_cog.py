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
    force_epsg4326: bool = Field(True, description="Force WGS84 (EPSG:4326) projection")
    convert_to_byte: bool = Field(False, description="Convert output to Byte (8-bit) for better preview compatibility")
    data_type: Optional[str] = Field(None, description="Override output data type (Byte, Int16, Float32)")
    additional_options: Dict[str, str] = Field(default_factory=dict, description="Additional GDAL options")
    overview_levels: Optional[List[int]] = Field(None, description="Specific overview levels to generate (e.g. [2, 4, 8, 16])")
    max_zoom: Optional[int] = Field(None, description="Maximum zoom level for TiTiler display")
    target_resolution: Optional[float] = Field(None, description="Target resolution in degrees for the output (e.g., 0.001)")
    
    def get_subdataset_path(self) -> str:
        """Get the full path to the specified NetCDF subdataset"""
        return f"NETCDF:\"{self.input_file}\":{self.subdataset}"
    
    def get_temp_file(self) -> str:
        """Get the temporary file path or generate one if not provided"""
        if not self.temp_file:
            return f"{os.path.splitext(self.output_file)[0]}_temp.tif"
        return self.temp_file


def get_dataset_bounds(file_path: str, dataset_type: DatasetType) -> Optional[Tuple[float, float, float, float]]:
    """
    Get the actual bounds of the dataset from the NetCDF file
    
    Args:
        file_path: Path to the NetCDF file
        dataset_type: Type of dataset (ABI_GOES19, LEO, etc.)
        
    Returns:
        Tuple containing (xmin, ymin, xmax, ymax) or None if bounds cannot be determined
    """
    # Use ncdump to get bounds from global attributes
    try:
        cmd = ["ncdump", "-h", file_path]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        output = result.stdout
        
        # Parse for bounds attributes
        bounds = {}
        for attr in ["westernmost_longitude", "easternmost_longitude", 
                     "southernmost_latitude", "northernmost_latitude"]:
            for line in output.split('\n'):
                line = line.strip()
                if f":{attr}" in line and '=' in line:
                    value_str = line.split('=')[1].strip()
                    # Remove trailing semicolon, f suffix, etc.
                    value_str = value_str.rstrip(';').rstrip('f').strip()
                    try:
                        bounds[attr] = float(value_str)
                        break
                    except ValueError:
                        pass
        
        # Check if we have all the bounds
        required_bounds = ["westernmost_longitude", "easternmost_longitude", 
                           "southernmost_latitude", "northernmost_latitude"]
        if all(key in bounds for key in required_bounds):
            return (
                bounds["westernmost_longitude"],
                bounds["southernmost_latitude"],
                bounds["easternmost_longitude"],
                bounds["northernmost_latitude"]
            )
    except Exception as e:
        print(f"Warning: Error extracting bounds using ncdump: {str(e)}")
    
    # Fallback to using gdalinfo on the subdataset
    try:
        subdataset_path = f"NETCDF:\"{file_path}\":{DatasetType.ABI_GOES19.value}"
        cmd = ["gdalinfo", subdataset_path]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        output = result.stdout
        
        # Extract corner coordinates
        corners = {}
        in_corners_section = False
        for line in output.split('\n'):
            if "Corner Coordinates:" in line:
                in_corners_section = True
                continue
            
            if in_corners_section:
                if "Upper Left" in line:
                    parts = line.split('(')[1].split(')')[0].split(',')
                    corners["xmin"] = float(parts[0].strip())
                    corners["ymax"] = float(parts[1].strip())
                elif "Lower Right" in line:
                    parts = line.split('(')[1].split(')')[0].split(',')
                    corners["xmax"] = float(parts[0].strip())
                    corners["ymin"] = float(parts[1].strip())
                elif not line.strip() or "Center" in line:
                    break
        
        if "xmin" in corners and "ymin" in corners and "xmax" in corners and "ymax" in corners:
            return (corners["xmin"], corners["ymin"], corners["xmax"], corners["ymax"])
    except Exception as e:
        print(f"Warning: Error extracting bounds using gdalinfo: {str(e)}")
    
    # Use defaults for known dataset types
    if dataset_type == DatasetType.LEO:
        return (-85.0, 23.0, -77.0, 31.02)
    elif dataset_type == DatasetType.ABI_GOES19:
        return (-156.19, -81.15, 6.19, 81.15)
    
    # Unable to determine bounds
    return None


def get_dataset_info(dataset_path: str) -> Dict:
    """
    Get information about a dataset using gdalinfo
    
    Args:
        dataset_path: Path to the dataset
        
    Returns:
        Dictionary with dataset information
    """
    info = {
        "data_type": None,
        "min_value": None,
        "max_value": None,
        "no_data": None,
        "scale": None,
        "offset": None
    }
    
    try:
        cmd = ["gdalinfo", "-stats", dataset_path]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        output = result.stdout.split('\n')
        
        for line in output:
            line = line.strip()
            if "Type=" in line:
                data_type = line.split("Type=")[1].split(",")[0]
                info["data_type"] = data_type
            elif "Minimum=" in line and "Maximum=" in line:
                parts = line.split(",")
                for part in parts:
                    if "Minimum=" in part:
                        min_value = float(part.split("=")[1])
                        info["min_value"] = min_value
                    elif "Maximum=" in part:
                        max_value = float(part.split("=")[1])
                        info["max_value"] = max_value
            elif "NoData Value=" in line:
                no_data = line.split("=")[1].strip()
                info["no_data"] = float(no_data)
            elif "Offset:" in line:
                offset = float(line.split(":")[1].split(",")[0].strip())
                info["offset"] = offset
            elif "Scale:" in line:
                scale = float(line.split(":")[1].strip())
                info["scale"] = scale
    except Exception as e:
        print(f"Warning: Error getting dataset info: {str(e)}")
    
    return info


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
    intermediate_file = f"{os.path.splitext(temp_file)[0]}_int.tif"
    
    # Get dataset bounds if needed and not explicitly specified
    dataset_bounds = None
    if config.preserve_subset and not config.bbox:
        dataset_bounds = get_dataset_bounds(config.input_file, config.dataset_type)
        if dataset_bounds:
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
    
    # Add target resolution if specified
    if config.target_resolution:
        warp_cmd.extend(["-tr", str(config.target_resolution), str(config.target_resolution)])
    
    # Always set the source and target CRS to ensure proper georeferencing
    if config.force_epsg4326:
        warp_cmd.extend(["-t_srs", "EPSG:4326"])
    
    # Add bounds - either explicitly specified or detected from the dataset
    if config.bbox:
        warp_cmd.extend(["-te", *config.bbox.split(",")])
    elif dataset_bounds:
        warp_cmd.extend(["-te", str(dataset_bounds[0]), str(dataset_bounds[1]), 
                        str(dataset_bounds[2]), str(dataset_bounds[3])])
    
    # Specify output data type if provided
    if config.data_type:
        warp_cmd.extend(["-ot", config.data_type])
    
    # Add input and output files
    warp_cmd.extend([subdataset_path, temp_file])
    
    # Execute gdalwarp command
    print(f"Executing: {' '.join(warp_cmd)}")
    subprocess.run(warp_cmd, check=True)
    
    # Get information about the warped dataset
    dataset_info = get_dataset_info(temp_file)
    print(f"Dataset info: {dataset_info}")
    
    # Special handling for LEO dataset (Float32 with negative nodata)
    if config.dataset_type == DatasetType.LEO or config.convert_to_byte:
        min_valid = dataset_info.get("min_value", 0)
        max_valid = dataset_info.get("max_value", 50)
        
        # Ensure we have reasonable min/max values
        if min_valid is None or max_valid is None or min_valid == max_valid:
            # Get valid range from file metadata
            try:
                cmd = ["gdalinfo", temp_file]
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if "valid_min=" in line:
                        min_valid = float(line.split("valid_min=")[1].split(",")[0].strip("-{} "))
                    if "valid_max=" in line:
                        max_valid = float(line.split("valid_max=")[1].strip("-{} "))
            except Exception:
                # Default to reasonable values for SST data
                min_valid = 0
                max_valid = 35
        
        # Convert to scaled Byte or UInt16 for better preview compatibility
        scale_cmd = [
            "gdal_translate",
            "-of", "GTiff",
            "-ot", "Byte" if 0 <= min_valid <= 255 and 0 <= max_valid <= 255 else "UInt16",
            "-scale", str(min_valid), str(max_valid), "0", "255" if 0 <= min_valid <= 255 and 0 <= max_valid <= 255 else "65535",
            "-a_nodata", "0",  # Use 0 as NoData for better preview compatibility
            "-co", f"COMPRESS={config.compression}",
            "-co", f"PREDICTOR={config.predictor}",
            "-co", "BIGTIFF=YES",
            temp_file,
            intermediate_file
        ]
        
        print(f"Executing scaling command: {' '.join(scale_cmd)}")
        subprocess.run(scale_cmd, check=True)
        
        # Now convert the scaled file to COG
        input_for_cog = intermediate_file
    else:
        # For other formats, use the warped file directly
        input_for_cog = temp_file
    
    # Set default overview levels if not specified
    if not config.overview_levels:
        config.overview_levels = [2, 4, 8, 16, 32, 64, 128, 256, 512]
    
    # Convert to COG
    cog_cmd = [
        "gdal_translate",
        "-of", "COG",
        "-co", f"COMPRESS={config.compression}",
        "-co", f"PREDICTOR={config.predictor}",
        "-co", "BIGTIFF=YES",
    ]
    
    # Add overview settings with specific overview levels
    if config.create_overviews:
        # Convert overview levels to string
        overview_levels_str = ",".join(map(str, config.overview_levels))
        cog_cmd.extend(["-co", f"OVERVIEW_RESAMPLING={config.resample_method}"])
        cog_cmd.extend(["-co", f"OVERVIEWS={overview_levels_str}"])
    
    # Add blocksize for optimal tiling
    cog_cmd.extend(["-co", "BLOCKSIZE=512"])
    
    # Set max zoom level if specified
    if config.max_zoom:
        cog_cmd.extend(["-co", f"MAX_ZOOM_LEVEL={config.max_zoom}"])
    
    # Add any additional options
    for key, value in config.additional_options.items():
        if key.startswith("cog_"):
            option_name = key.replace("cog_", "")
            cog_cmd.extend([f"-co", f"{option_name}={value}"])
    
    cog_cmd.extend([input_for_cog, config.output_file])
    
    print(f"Executing: {' '.join(cog_cmd)}")
    subprocess.run(cog_cmd, check=True)
    
    # Clean up temporary files
    if os.path.exists(temp_file):
        os.remove(temp_file)
    if os.path.exists(intermediate_file):
        os.remove(intermediate_file)
        
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
            force_epsg4326=True,
            predictor=2,  # Default works for all data types
            overview_levels=[2, 4, 8, 16, 32, 64, 128, 256],
            max_zoom=12  # Provide enough zoom levels for ABI-GOES19
        ),
        DatasetType.LEO: ProcessingConfig(
            dataset_type=DatasetType.LEO,
            input_file="data/LEO-2025-05-01T000000Z.nc",
            output_file="data/LEO-2025-05-01T000000Z_SST_cog.tif",
            subdataset="sea_surface_temperature",
            resample_method="bilinear",
            preserve_subset=True,
            force_epsg4326=True,
            convert_to_byte=True,  # Convert Float32 to Byte format for better preview compatibility
            predictor=2,  # Default works for all data types
            target_resolution=0.002,  # Higher resolution (~200m at equator) for LEO data
            overview_levels=[2, 4, 8, 16, 32, 64, 128, 256],
            max_zoom=14  # Higher zoom level for more detailed LEO data
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