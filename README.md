# Salty Tiler

A TiTiler-based microservice for processing ocean datasets (SST, chlorophyll) from NetCDF to cloud-optimized GeoTIFFs and serving them as map tiles. This service is designed to be integrated into larger application pipelines as a standalone tile rendering service.

## Overview

Salty Tiler provides a FastAPI + TiTiler service that:

1. Converts NetCDF ocean datasets to Cloud-Optimized GeoTIFFs (COGs)
2. Serves map tiles with custom colormaps and dynamic scaling
3. Handles temperature unit conversion (C/K → F) automatically
4. Provides metadata endpoints for dataset ranges

**Note**: This is a backend tile service. The included Mapbox viewer is for debugging/testing only and will not be part of production deployments.

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

### Debug Viewer (Development Only)

A Mapbox GL JS frontend is included for testing and debugging tile rendering. **This viewer is for development/debugging purposes only and will not be part of production deployments.**

#### Quick Start (Debug Only)

1. Open a new terminal and navigate to the viewer:

   ```bash
   cd mapbox-viewer
   npm install
   npm run dev
   ```

2. This will open the debug viewer at [http://localhost:3000](http://localhost:3000).

3. Make sure the tile server is running at [http://127.0.0.1:8001](http://127.0.0.1:8001).

4. Use the viewer to test tile rendering, colormaps, and value ranges during development.

## TiTiler Integration & File Format Requirements

### How TiTiler Works

TiTiler is a dynamic tile server that renders map tiles on-demand from Cloud-Optimized GeoTIFFs (COGs). It provides:

- **Dynamic Rendering**: Tiles are generated in real-time with custom styling
- **Multiple Formats**: Supports PNG, JPEG, WebP output formats
- **Custom Colormaps**: Apply color palettes to single-band raster data
- **Value Scaling**: Rescale data values for optimal visualization
- **Resampling**: Bilinear, nearest, cubic interpolation options

### File Format Requirements

#### Input: NetCDF Files

Your application should download NetCDF files with these characteristics:

- **Variables**: Single data variable (e.g., `sea_surface_temperature`, `chlor_a`)
- **Dimensions**: `(time, latitude, longitude)` or `(latitude, longitude)`
- **CRS Information**: Lat/lon coordinates with proper metadata
- **Units**: Temperature in Celsius or Kelvin, chlorophyll in mg/m³

#### Output: Cloud-Optimized GeoTIFFs (COGs)

The conversion process creates COGs optimized for tile serving:

- **Format**: GeoTIFF with COG structure
- **Tiling**: 512x512 pixel internal tiles
- **Overviews**: Multiple resolution levels (2x, 4x, 8x, 16x, 32x)
- **Compression**: DEFLATE with predictor for efficient storage
- **Projection**: EPSG:4326 (WGS84) for web compatibility

### Integration Workflow

1. **Download NetCDF**: Your app downloads ocean data files
2. **Convert to COG**: Use `convert_all_nc_to_cog.py` or integrate conversion logic
3. **Store COGs**: Place COG files in accessible storage (local, S3, etc.)
4. **Tile Requests**: Frontend requests tiles via TiTiler endpoints
5. **Dynamic Rendering**: TiTiler generates tiles with custom styling

### API Endpoints for Integration

#### Direct COG Tiles

```
GET /cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png
```

Parameters:

- `url`: Path to COG file
- `rescale`: Min,max values (e.g., `32,86`)
- `colormap_name`: Named colormap (e.g., `sst_high_contrast`)
- `resampling`: Interpolation method (`bilinear`, `nearest`, `cubic`)

#### Entry-Based Tiles (with Database)

```
GET /tiles/{entry_id}/{z}/{x}/{y}.png
```

Parameters:

- `entry_id`: Database entry UUID
- `min`, `max`: Value range for scaling
- `layer`: Layer key (default: `geotiff`)

#### Metadata

```
GET /metadata/{dataset}/range
```

Returns min/max values for dataset scaling.

### Performance Considerations

- **COG Structure**: Internal tiling and overviews enable efficient partial reads
- **Caching**: Implement tile caching at CDN/application level
- **Storage**: Use fast storage (SSD, S3) for COG files
- **Scaling**: TiTiler can be horizontally scaled behind load balancer

## API Documentation

API docs are available at:

- http://127.0.0.1:8001/docs (Swagger UI)
- http://127.0.0.1:8001/redoc (ReDoc)

## Service Integration

### Deployment as Microservice

This service is designed to be deployed as a standalone microservice in your application architecture:

```
Your App Pipeline:
1. Download NetCDF files
2. Convert to COGs (using conversion logic from this repo)
3. Store COGs in accessible location
4. Make tile requests to Salty Tiler service
5. Serve tiles to frontend mapping components
```

### Docker Deployment (Recommended)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Environment Variables

- `TILER_HOST`: Host address (default: 0.0.0.0)
- `TILER_PORT`: Port number (default: 8001)
- `COG_BASE_PATH`: Base path for COG files
- `SUPABASE_URL`: Supabase project URL (if using database integration)
- `SUPABASE_KEY`: Supabase API key

### Health Check Endpoint

```
GET /health
```

Returns service status for load balancer health checks.

## Configuration

The application uses several configuration files:

- `sst_colormap.json` - Custom colormap for rendering
- `routes/metadata.py` - Dataset ranges
- `mock_supabase.py` - Entry lookup (replace with real Supabase in production)

## Project Structure

```
salty-tiler/                  # TiTiler Microservice
├── app.py                    # Main FastAPI application
├── start.py                  # Development start script
├── convert_all_nc_to_cog.py  # NetCDF to COG converter (integrate into your app)
├── sst_colormap.json         # Custom palette definition
├── mock_supabase.py          # Entry lookup (replace with real DB)
├── routes/
│   ├── metadata.py           # Dataset metadata endpoints
│   └── tiles.py              # Tile endpoints
├── schemas/
│   └── entry.py              # Pydantic models for entries
├── services/
│   └── tiler.py              # Tile rendering service
├── mapbox-viewer/            # Debug viewer (development only)
├── cogs/                     # COG files storage
└── raw_netcdf/               # NetCDF files (for testing)
```

### Key Files for Integration

- **`app.py`**: Main FastAPI application - deploy this as your microservice
- **`convert_all_nc_to_cog.py`**: NetCDF conversion logic - integrate into your app's data pipeline
- **`routes/tiles.py`**: Tile serving endpoints - the core API your frontend will call
- **`services/tiler.py`**: TiTiler wrapper - handles the actual tile rendering
- **`sst_colormap.json`**: Color palettes - customize for your data visualization needs

## License

MIT
