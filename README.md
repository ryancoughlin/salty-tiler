# Salty Tiler

A complete toolkit for processing ocean datasets (SST, chlorophyll) from NetCDF to cloud-optimized GeoTIFFs and serving them through a TiTiler-based API. Includes temperature unit conversion (C/K to F) and custom palette rendering.

## Features

- **Data Processing**:
  - Convert NetCDF datasets to Cloud-Optimized GeoTIFFs (COGs)
  - Support for multiple sources (ABI-GOES19, LEO, VIIRS)
  - Automatic detection of units and CRS
  - Temperature conversion (C/K → F)
  - Generation of overviews for efficient tiling
- **Tile Server**:
  - FastAPI + TiTiler based API for rendering tiles
  - Custom colormap support for ocean data visualization
  - Metadata endpoints for dataset ranges
  - Configurable min/max value scaling
  - Entry-based lookup (with Supabase integration support)

## Installation

1. Clone this repository:

   ```
   git clone <repository-url>
   cd salty-tiler
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

### Data Conversion

Convert NetCDF files to COGs:

```bash
python convert_all_nc_to_cog.py
```

This will:

1. Process all .nc files in `raw_netcdf/` directory
2. Extract variables like 'sea_surface_temperature' or 'chlor_a'
3. Convert temperature units to Fahrenheit if needed
4. Create optimized COGs in the `cogs/` directory

### Running the Tile Server

#### Quick Start

The simplest way to start everything is:

```bash
python start.py
```

This will:

1. Start a static file server for COGs on port 8000
2. Start the TiTiler API on port 8001
3. Open the API documentation in your browser

#### Manual Start

Alternatively, you can start components individually:

1. Start the static file server:

   ```bash
   python -m http.server 8000
   ```

2. Start the TiTiler API:
   ```bash
   python app.py
   ```

This will launch a FastAPI application at http://127.0.0.1:8001/ with these endpoints:

- `/cog/tiles/{z}/{x}/{y}.png` - Standard TiTiler COG tiles endpoint
- `/tiles/{entry_id}/{z}/{x}/{y}.png` - Entry-based tiles (using Supabase lookup)
- `/metadata/{dataset}/range` - Get min/max range for a dataset

### Example API Usage

Fetch a tile using the entry-based endpoint:

```
http://localhost:8001/tiles/test-entry-1/6/12/20.png?min=32&max=86
```

Fetch a tile directly using the COG endpoint:

```
http://localhost:8001/cog/tiles/WebMercatorQuad/6/12/20.png?url=cogs/sst_keys_2025-05-01.tif&rescale=32,86&colormap_name=sst_high_contrast
```

## API Documentation

API docs are available at:

- http://127.0.0.1:8001/docs (Swagger UI)
- http://127.0.0.1:8001/redoc (ReDoc)

## Configuration

The application uses several configuration files:

- `my_palette.json` - Custom colormap for rendering
- `routes/metadata.py` - Dataset ranges
- `mock_supabase.py` - Entry lookup (replace with real Supabase in production)

## Project Structure

```
salty-tiler/
├── app.py                    # Main FastAPI application
├── start.py                  # Start script for all services
├── convert_all_nc_to_cog.py  # NetCDF to COG converter
├── my_palette.json           # Custom palette definition
├── mock_supabase.py          # Entry lookup (for demo)
├── routes/
│   ├── metadata.py           # Dataset metadata endpoints
│   └── tiles.py              # Tile endpoints
├── schemas/
│   └── entry.py              # Pydantic models for entries
├── services/
│   └── tiler.py              # Tile rendering service
├── cogs/                     # Output COGs directory
└── raw_netcdf/               # Input NetCDF directory
```

## License

MIT
