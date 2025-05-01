#!/usr/bin/env python
"""
Create High-Resolution COG for Fishing Applications

This script creates a high-resolution Cloud-Optimized GeoTIFF from NetCDF data,
optimized for fishing applications with detailed temperature gradients.
"""
import os
import subprocess
import tempfile
from pathlib import Path

# Input and output paths
INPUT_FILE = "data/LEO-2025-05-01T000000Z.nc"
SUBDATASET = "sea_surface_temperature"
OUTPUT_FILE = "data/LEO-2025-05-01T000000Z_highres_cog.tif"
TEMP_DIR = tempfile.mkdtemp()

# Parameters for high-resolution conversion
RESOLUTION = 0.0005  # ~50 meters at equator, much higher than original
BBOX = "-85,23,-77,31.02"  # Florida region
RESAMPLING = "cubic"  # Better quality for temperature data

# Temperature range for visualization (in Celsius for the input data)
MIN_TEMP_C = 21.0  # Minimum expected temperature
MAX_TEMP_C = 30.0  # Maximum expected temperature

def create_high_res_tif():
    """
    Step 1: Create a high-resolution GeoTIFF with gdalwarp
    """
    # Temporary file for intermediate high-res GeoTIFF
    temp_file = os.path.join(TEMP_DIR, "highres_temp.tif")
    
    # Build gdalwarp command for high-resolution output
    subdataset_path = f"NETCDF:\"{INPUT_FILE}\":{SUBDATASET}"
    warp_cmd = [
        "gdalwarp",
        "-overwrite",
        "-of", "GTiff",
        "-r", RESAMPLING,
        "-tr", str(RESOLUTION), str(RESOLUTION),  # High-resolution output
        "-t_srs", "EPSG:4326",
        "-te", *BBOX.split(","),  # Set bounding box
        "-co", "COMPRESS=DEFLATE",
        "-co", "PREDICTOR=2",
        "-co", "TILED=YES",
        "-co", "BLOCKXSIZE=512",
        "-co", "BLOCKYSIZE=512",
        "-co", "BIGTIFF=YES",
        subdataset_path,
        temp_file
    ]
    
    print(f"Creating high-resolution GeoTIFF...")
    print(f"Executing: {' '.join(warp_cmd)}")
    subprocess.run(warp_cmd, check=True)
    
    # Get information about the warped dataset
    info_cmd = ["gdalinfo", "-stats", temp_file]
    result = subprocess.run(info_cmd, capture_output=True, text=True, check=True)
    
    # Extract min/max values from stats
    min_val, max_val = None, None
    for line in result.stdout.split('\n'):
        if "Minimum=" in line and "Maximum=" in line:
            parts = line.split(',')
            for part in parts:
                if "Minimum=" in part:
                    min_val = float(part.split('=')[1])
                elif "Maximum=" in part:
                    max_val = float(part.split('=')[1])
    
    print(f"Temperature range in data: {min_val}°C to {max_val}°C")
    
    return temp_file, min_val, max_val

def convert_to_byte_tif(input_file, min_val, max_val):
    """
    Step 2: Convert to byte representation for better visualization
    """
    # Use actual min/max if available, otherwise use default range
    min_temp = min_val if min_val is not None else MIN_TEMP_C
    max_temp = max_val if max_val is not None else MAX_TEMP_C
    
    # Adjust slightly to ensure we cover the full range
    min_temp = max(1, min_temp - 1)  # Avoid going below 0 for Byte representation
    max_temp = min(40, max_temp + 1)  # Limit to reasonable max temp for ocean water
    
    print(f"Scaling temperature from {min_temp}°C-{max_temp}°C to 1-254 range")
    
    # Create 8-bit representation for visualization
    byte_file = os.path.join(TEMP_DIR, "highres_byte.tif")
    scale_cmd = [
        "gdal_translate",
        "-ot", "Byte",
        "-scale", str(min_temp), str(max_temp), "1", "254",  # Reserve 0 for nodata, 255 for max
        "-a_nodata", "0",
        "-co", "COMPRESS=DEFLATE",
        "-co", "PREDICTOR=2",
        "-co", "TILED=YES",
        "-co", "BLOCKXSIZE=512",
        "-co", "BLOCKYSIZE=512",
        input_file,
        byte_file
    ]
    
    print(f"Creating 8-bit visualization...")
    print(f"Executing: {' '.join(scale_cmd)}")
    subprocess.run(scale_cmd, check=True)
    
    # Add temperature range metadata for TiTiler
    set_metadata_cmd = [
        "gdal_edit.py",
        "-mo", f"TEMPERATURE_RANGE={min_temp},{max_temp}",
        "-mo", "UNITS=Celsius",
        "-mo", "COLORMAP=viridis",
        byte_file
    ]
    
    print(f"Adding metadata...")
    subprocess.run(set_metadata_cmd, check=True)
    
    return byte_file

def convert_to_cog(input_file):
    """
    Step 3: Convert to web-optimized COG using rio-cogeo
    """
    # Use rio-cogeo with optimal settings for web visualization
    cog_cmd = [
        "rio", "cogeo", "create",
        input_file,
        OUTPUT_FILE,
        "--co", "COMPRESS=DEFLATE",
        "--co", "PREDICTOR=2",
        "--overview-level", "6",  # Create 6 overview levels
        "--overview-resampling", RESAMPLING,
        "--web-optimized",  # Structure optimally for web clients
        "--quiet"
    ]
    
    print(f"\nCreating Cloud-Optimized GeoTIFF...")
    print(f"Executing: {' '.join(cog_cmd)}")
    subprocess.run(cog_cmd, check=True)

def main():
    """Main processing function"""
    try:
        # Step 1: Create high-resolution GeoTIFF
        temp_file, min_val, max_val = create_high_res_tif()
        
        # Step 2: Convert to byte representation for visualization
        byte_file = convert_to_byte_tif(temp_file, min_val, max_val)
        
        # Step 3: Convert to COG
        convert_to_cog(byte_file)
        
        # Validate the output
        print(f"\nValidating final COG...")
        validate_cmd = ["gdalinfo", OUTPUT_FILE]
        subprocess.run(validate_cmd, check=True)
        
        # Check tilejson with titiler (if running)
        print(f"\nTo test with TiTiler, open:")
        print(f"http://127.0.0.1:8001/cog/WebMercatorQuad/tilejson.json?url={OUTPUT_FILE}")
        
        # URL for visualization with colormap
        print(f"\nVisualize with colormap:")
        print(f"http://127.0.0.1:8001/cog/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}?url={OUTPUT_FILE}&colormap_name=viridis")
        
        print(f"\nSuccessfully created high-resolution COG: {OUTPUT_FILE}")
    
    finally:
        # Clean up temporary files
        for file in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(TEMP_DIR)

if __name__ == "__main__":
    main() 