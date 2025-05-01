# NetCDF to Cloud-Optimized GeoTIFF Converter

A flexible, configuration-based tool for converting various NetCDF datasets (ABI-GOES19, LEO, etc.) to Cloud-Optimized GeoTIFFs (COGs), preserving high resolution and data quality.

## Features

- Support for multiple NetCDF dataset types
- Configuration-based approach for different processing parameters
- Batch processing capability
- Preservation of high-resolution data and original geospatial properties
- Customizable resampling methods and compression options
- JSON configuration export/import

## Installation

1. Clone this repository:

   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Run the script with default configurations:

```bash
python convert_nc_to_cog.py
```

This will process both ABI-GOES19 and LEO datasets with their respective default configurations.

### Custom Configuration

You can create and save custom configurations:

```python
from convert_nc_to_cog import ProcessingConfig, DatasetType, save_config

# Create a custom configuration
config = ProcessingConfig(
    dataset_type=DatasetType.LEO,
    input_file="path/to/your/file.nc",
    output_file="path/to/output.tif",
    subdataset="sea_surface_temperature",
    resample_method="cubic",  # Higher quality resampling
    additional_options={"warp_dstnodata": "-9999"}  # Extra GDAL options
)

# Save the configuration for later use
save_config(config, "configs/my_custom_config.json")
```

Then load and use it:

```python
from convert_nc_to_cog import load_config, process_file

# Load a saved configuration
config = load_config("configs/my_custom_config.json")

# Process a file with this configuration
output_file = process_file(config)
```

### Processing Multiple Files

```python
from convert_nc_to_cog import ProcessingConfig, DatasetType, batch_process

configs = [
    ProcessingConfig(
        dataset_type=DatasetType.ABI_GOES19,
        input_file="data/file1.nc",
        output_file="data/file1_cog.tif",
        subdataset="sea_surface_temperature"
    ),
    ProcessingConfig(
        dataset_type=DatasetType.LEO,
        input_file="data/file2.nc",
        output_file="data/file2_cog.tif",
        subdataset="sea_surface_temperature"
    )
]

output_files = batch_process(configs)
```

## Supported Dataset Types

Currently supported dataset types:

1. **ABI_GOES19** - GOES-19 Advanced Baseline Imager data
2. **LEO** - Low Earth Orbit satellite data

## Configuration Options

| Option             | Description                                 | Default                   |
| ------------------ | ------------------------------------------- | ------------------------- |
| dataset_type       | Type of NetCDF dataset                      | (required)                |
| input_file         | Path to input NetCDF file                   | (required)                |
| output_file        | Path to output COG file                     | (required)                |
| subdataset         | NetCDF subdataset to extract                | "sea_surface_temperature" |
| temp_file          | Optional path for temporary file            | (auto-generated)          |
| bbox               | Optional bounding box (xmin,ymin,xmax,ymax) | None                      |
| resample_method    | Resampling method for gdalwarp              | "bilinear"                |
| create_overviews   | Whether to create overviews                 | True                      |
| compression        | Compression method                          | "DEFLATE"                 |
| predictor          | Predictor value for compression             | 2                         |
| additional_options | Additional GDAL options                     | {}                        |

### Note About Spatial Extent

The system now assumes that input data is already in the correct spatial format and preserves the original extent. The `bbox` parameter is optional and only needs to be specified if you explicitly want to clip or subset the data to a specific geographic region.

## Requirements

- Python 3.8+
- GDAL (with Python bindings)
- Pydantic

## License

MIT
