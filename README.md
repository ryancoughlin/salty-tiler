# Salty Tiler

A TiTiler-based microservice for serving ocean dataset tiles from external COG URLs. This service is designed to work with the salty-data-processor pipeline, consuming COG files from external storage and serving them as map tiles with custom colormaps and dynamic scaling.

## Overview

Salty Tiler provides a FastAPI + TiTiler service that:

1. **Serves map tiles from external COG URLs** (e.g., `https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif`)
2. **Validates COG availability** before attempting to render tiles
3. **Applies custom colormaps** and dynamic scaling for ocean data visualization
4. **Handles temperature unit conversion** (C/K → F) automatically
5. **Provides metadata endpoints** for dataset ranges

## Features

- **External COG Support**: Renders tiles from COG URLs hosted on external services
- **Custom Colormaps**: High-contrast SST colormap optimized for ocean data
- **Dynamic Scaling**: Configurable min/max value ranges for optimal visualization
- **COG Validation**: Validates COG availability before tile rendering
- **Docker Ready**: Complete Docker deployment with health checks
- **Performance**: LRU caching and bilinear resampling for smooth rendering

## Quick Start

### Docker Deployment (Recommended)

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd salty-tiler
   ```

2. Copy environment configuration:

   ```bash
   cp env.example .env
   ```

3. Deploy with Docker:
   ```bash
   ./deploy.sh
   ```

The service will be available at `http://localhost:8001` with API documentation at `/docs`.

### Local Development

1. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the service:
   ```bash
   python app.py
   ```

## API Endpoints

### Tile Endpoints

#### Structured Path Tiles

```
GET /tiles/{dataset}/{region}/{timestamp}/{z}/{x}/{y}.png
```

Constructs COG URL from path components.

**Parameters:**

- `dataset`: Dataset name (e.g., `sst_composite`, `chlor_a`)
- `region`: Region name (e.g., `ne_canyons`, `florida_keys`)
- `timestamp`: ISO timestamp (e.g., `2025-07-13T070646Z`)
- `z/x/y`: Tile coordinates
- `min`, `max`: Value range for scaling (query params)
- `base_url`: COG base URL (query param, optional)

**Example:**

```
http://localhost:8001/tiles/sst_composite/ne_canyons/2025-07-13T070646Z/6/12/20.png?min=32&max=86
```

#### Direct URL Tiles

```
GET /tiles/{z}/{x}/{y}.png
```

Accepts full COG URL as parameter.

**Parameters:**

- `z/x/y`: Tile coordinates
- `url`: Full COG URL (query param)
- `min`, `max`: Value range for scaling (query params)
- `dataset`: Dataset type for colormap selection (query param)

**Example:**

```
http://localhost:8001/tiles/6/12/20.png?url=https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif&min=32&max=86&dataset=sst
```

#### TiTiler Direct

```
GET /cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png
```

Standard TiTiler endpoint for advanced usage.

**Parameters:**

- `url`: COG URL
- `rescale`: Min,max values (e.g., `32,86`)
- `colormap_name`: Named colormap (e.g., `sst_high_contrast`)
- `resampling`: Interpolation method (`bilinear`, `nearest`, `cubic`)

### Metadata Endpoints

#### Dataset Range

```
GET /metadata/{dataset}/range
```

Returns min/max values for dataset scaling.

#### Health Check

```
GET /health
```

Health check endpoint for load balancers.

## Configuration

### Environment Variables

- `TILER_HOST`: Host address (default: `0.0.0.0`)
- `TILER_PORT`: Port number (default: `8001`)
- `COG_BASE_URL`: Base URL for external COG files (default: `https://data.saltyoffshore.com`)
- `CORS_ORIGINS`: CORS allowed origins (default: `*`)
- `TILE_CACHE_SIZE`: LRU cache size for tiles (default: `2048`)

### COG URL Format

The service expects COG files to be available at:

```
{base_url}/{region}/{dataset}/{timestamp}_cog.tif
```

Example:

```
https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif
```

## Integration with salty-data-processor

This service is designed to work with the salty-data-processor pipeline:

1. **salty-data-processor** downloads NetCDF files and converts them to COGs
2. **COGs are stored** at external URLs (e.g., `https://data.saltyoffshore.com`)
3. **salty-tiler** serves tiles from these external COG URLs
4. **Frontend applications** request tiles with dynamic scaling and colormaps

## Docker Management

### Deploy Service

```bash
./deploy.sh
```

### View Logs

```bash
./deploy.sh logs
```

### Check Status

```bash
./deploy.sh status
```

### Stop Service

```bash
./deploy.sh stop
```

### Restart Service

```bash
./deploy.sh restart
```

## Testing

Test the service with the provided test script:

```bash
python test_external_cog.py
```

This will verify:

- Health check endpoint
- Direct URL tile endpoint
- Structured path tile endpoint
- Metadata endpoint
- TiTiler direct endpoint

## Performance

- **COG Validation**: Service validates COG availability before rendering
- **LRU Caching**: Configurable tile caching for improved performance
- **Bilinear Resampling**: Smooth tile interpolation for better visual quality
- **Custom Colormaps**: Optimized color palettes for ocean data visualization

## API Documentation

Interactive API documentation is available at:

- `http://localhost:8001/docs` (Swagger UI)
- `http://localhost:8001/redoc` (ReDoc)

## License

MIT
