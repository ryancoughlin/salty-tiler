# Salty Tiler

A TiTiler-based microservice for serving ocean dataset tiles from external COG URLs.

## Quick Start

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

1. **Install uv** (if not already installed):
   ```bash
   pip install uv
   ```

2. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd salty-tiler
   ```

3. **Install dependencies**:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

4. **Run the service**:
   ```bash
   python app.py
   ```

The service will be available at `http://localhost:8001` with API docs at `/docs`.

## Docker Deployment

```bash
# Deploy with Docker
./deploy.sh

# View logs
./deploy.sh logs

# Stop service
./deploy.sh stop
```

## API Endpoints

### Tile Endpoints

**Structured Path Tiles**:
```
GET /tiles/{dataset}/{region}/{timestamp}/{z}/{x}/{y}.png?min={min}&max={max}
```

**Direct URL Tiles**:
```
GET /tiles/{z}/{x}/{y}.png?url={cog_url}&min={min}&max={max}&dataset={dataset}
```

**TiTiler Direct**:
```
GET /cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url={cog_url}&rescale={min},{max}&colormap_name={colormap}
```

### Metadata Endpoints

- `GET /metadata/{dataset}/range` - Dataset min/max values
- `GET /health` - Health check

## Configuration

### Environment Variables
- `TILER_HOST`: Host address (default: `0.0.0.0`)
- `TILER_PORT`: Port number (default: `8001`)
- `COG_BASE_URL`: Base URL for COG files (default: `https://data.saltyoffshore.com`)
- `CACHE_TTL`: Cache duration in seconds (default: `86400`)

### COG URL Format
```
{base_url}/{region}/{dataset}/{timestamp}_cog.tif
```

Example:
```
https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif
```

## Performance Features

- **In-memory caching** with 24-hour TTL
- **GDAL optimizations** for remote COG access
- **Custom colormaps** for ocean data visualization
- **Temperature unit conversion** (C/K → F)
- **Bilinear resampling** for smooth tiles

## Testing

```bash
python test_external_cog.py
```

## License

MIT