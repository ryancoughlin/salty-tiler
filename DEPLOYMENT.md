# Salty Tiler Deployment Guide

## Overview

Salty Tiler is a microservice that serves ocean dataset tiles from external COG URLs. It's designed to work with the salty-data-processor pipeline.

## Quick Start

### 1. Docker Deployment (Recommended)

```bash
# Build and deploy with one command
./deploy.sh

# Or step by step:
./deploy.sh build
./deploy.sh deploy
```

### 2. Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional)
export TILER_HOST=0.0.0.0
export TILER_PORT=8001
export COG_BASE_URL=https://data.saltyoffshore.com

# Run the service
python app.py
```

## API Endpoints

### Tile Endpoints

1. **Direct URL Endpoint**

   ```
   GET /tiles/{z}/{x}/{y}.png?url={cog_url}&min={min}&max={max}&dataset={dataset}
   ```

   Example:

   ```
   http://localhost:8001/tiles/6/12/20.png?url=https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif&min=32&max=86&dataset=sst
   ```

2. **Structured Path Endpoint**

   ```
   GET /tiles/{dataset}/{region}/{timestamp}/{z}/{x}/{y}.png?min={min}&max={max}&base_url={base_url}
   ```

   Example:

   ```
   http://localhost:8001/tiles/sst_composite/ne_canyons/2025-07-13T070646Z/6/12/20.png?min=32&max=86&base_url=https://data.saltyoffshore.com
   ```

3. **TiTiler Direct Endpoint**

   ```
   GET /cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url={cog_url}&rescale={min},{max}&colormap_name={colormap}
   ```

   Example:

   ```
   http://localhost:8001/cog/tiles/WebMercatorQuad/6/12/20.png?url=https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif&rescale=32,86&colormap_name=sst_high_contrast
   ```

### Metadata Endpoints

1. **Dataset Range**

   ```
   GET /metadata/{dataset}/range
   ```

   Example:

   ```
   http://localhost:8001/metadata/sst/range
   ```

2. **Health Check**
   ```
   GET /health
   ```

## Configuration

### Environment Variables

| Variable          | Default                          | Description                |
| ----------------- | -------------------------------- | -------------------------- |
| `TILER_HOST`      | `0.0.0.0`                        | Host address               |
| `TILER_PORT`      | `8001`                           | Port number                |
| `COG_BASE_URL`    | `https://data.saltyoffshore.com` | Base URL for COG files     |
| `CORS_ORIGINS`    | `*`                              | CORS allowed origins       |
| `TILE_CACHE_SIZE` | `2048`                           | LRU cache size for tiles   |
| `WORKERS`         | `1`                              | Number of worker processes |

### COG URL Format

The service expects COG files to be available at:

```
{base_url}/{region}/{dataset}/{timestamp}_cog.tif
```

Example:

```
https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif
```

## Testing

Run the test suite to verify functionality:

```bash
# Start the service first
python app.py

# In another terminal, run tests
python test_external_cog.py
```

## Docker Commands

```bash
# Build image
./deploy.sh build

# Deploy container
./deploy.sh deploy

# View logs
./deploy.sh logs

# Check status
./deploy.sh status

# Stop service
./deploy.sh stop

# Restart service
./deploy.sh restart
```

## Docker Compose

For production deployment with docker-compose:

```bash
# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

## Integration with salty-data-processor

The salty-tiler is designed to work with COG files generated by the salty-data-processor. The expected workflow is:

1. **salty-data-processor** processes NetCDF files and generates COGs
2. **COGs are stored** at accessible URLs (e.g., `https://data.saltyoffshore.com/`)
3. **salty-tiler** serves tiles from these COG URLs
4. **Client applications** request tiles with dynamic scaling parameters

## Performance Considerations

- **Caching**: Tiles are cached in memory using LRU cache
- **COG Validation**: URLs are validated before tile rendering
- **Error Handling**: 404 responses for missing tiles/COGs
- **Concurrent Requests**: FastAPI handles concurrent tile requests efficiently

## Troubleshooting

### Common Issues

1. **GDAL version mismatch during Docker build**

   - The Docker image uses `osgeo/gdal:ubuntu-small-3.11.3` to ensure GDAL compatibility
   - This resolves the "Python bindings of GDAL X.X.X require at least libgdal X.X.X" error
   - No manual intervention needed - versions are automatically matched

2. **COG URL not accessible**

   - Check network connectivity
   - Verify COG file exists at the expected URL
   - Check CORS settings if accessing from browser

3. **Tile rendering fails**

   - Verify COG file is valid
   - Check min/max range values
   - Review server logs for detailed error messages

4. **Performance issues**
   - Increase `TILE_CACHE_SIZE` for better caching
   - Use multiple workers with `WORKERS` environment variable
   - Ensure COG files have proper overviews

### Logs

View service logs:

```bash
./deploy.sh logs
```

### Health Check

Check service health:

```bash
curl http://localhost:8001/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "salty-tiler"
}
```
