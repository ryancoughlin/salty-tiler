# Salty Tiler

A TiTiler-based microservice for serving ocean dataset tiles from external COG URLs. This service is designed to work with the salty-data-processor pipeline, consuming COG files from external storage and serving them as map tiles with custom colormaps and dynamic scaling.

## Overview

Salty Tiler provides a FastAPI + TiTiler service that:

1. **Serves map tiles from external COG URLs** (e.g., `https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif`)
2. **Validates COG availability** before attempting to render tiles
3. **Applies custom colormaps** and dynamic scaling for ocean data visualization
4. **Handles temperature unit conversion** (C/K → F) automatically
5. **Provides metadata endpoints** for dataset ranges
6. **Implements in-memory caching** for improved tile serving performance
7. **Optimizes GDAL configuration** for remote COG access performance

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

**Docker Environment Variables:**
- `CACHE_TTL=86400` - Cache duration in seconds (24 hours)
- `VSI_CACHE_SIZE=50000000` - GDAL VSI cache size (50MB)
- `GDAL_CACHEMAX=200` - GDAL block cache size (200MB)

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

## Performance Optimization

### Caching Implementation

Salty Tiler implements a two-layer caching strategy for optimal performance:

1. **In-Memory Application Cache**: 
   - Uses `aiocache` with `SimpleMemoryCache`
   - 24-hour TTL for tile responses
   - Shared across all users
   - Adds `X-Cache: HIT/MISS` headers for debugging

2. **HTTP Cache Headers**:
   - `Cache-Control: public, max-age=86400` 
   - Compatible with CDNs and browser caching
   - 24-hour client-side cache duration

### GDAL Configuration

The application automatically configures GDAL for optimal remote COG access:

```bash
# Essential optimizations applied on startup:
GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR        # Reduce GET/LIST requests
GDAL_CACHEMAX=200                             # 200MB GDAL cache
CPL_VSIL_CURL_CACHE_SIZE=200000000           # 200MB VSI cache  
VSI_CACHE=TRUE                               # Enable VSI caching
VSI_CACHE_SIZE=5000000                       # 5MB per file handle
GDAL_HTTP_MERGE_CONSECUTIVE_RANGES=YES       # Merge range requests
GDAL_HTTP_MULTIPLEX=YES                      # HTTP/2 multiplexing
GDAL_BAND_BLOCK_CACHE=HASHSET               # Optimized block cache
```

For additional GDAL configuration, source the provided `gdal.env` file:
```bash
source gdal.env
```

### Performance Benefits

- **First request**: Downloads and caches tile (~20KB response)
- **Subsequent requests**: Serves from cache (~52 bytes response)  
- **Speed improvement**: 1.5-10x faster tile serving
- **Reduced bandwidth**: 99.7% reduction in repeated tile requests

Based on [TiTiler performance tuning recommendations](https://developmentseed.org/titiler/advanced/performance_tuning/).

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

## SwiftUI + Mapbox v11 Integration

### Basic Implementation

Here's how to implement the tile endpoints in SwiftUI with Mapbox v11:

```swift
import SwiftUI
import MapboxMaps

struct OceanDataMapView: View {
    @State private var map = Map()
    @State private var sstMinValue: Double = 32.0
    @State private var sstMaxValue: Double = 86.0

    private let tilerBaseURL = "http://localhost:8001"
    private let cogBaseURL = "https://data.saltyoffshore.com"

    var body: some View {
        VStack {
            // Map view
            MapReader { proxy in
                Map(map: map)
                    .onAppear {
                        setupOceanLayers()
                    }
            }

            // Controls
            VStack {
                Text("SST Range: \(Int(sstMinValue))°F - \(Int(sstMaxValue))°F")

                HStack {
                    Text("\(Int(sstMinValue))°F")
                    Slider(value: $sstMinValue, in: 32...86) { _ in
                        updateSSTLayer()
                    }
                    Text("\(Int(sstMaxValue))°F")
                }

                HStack {
                    Text("\(Int(sstMinValue))°F")
                    Slider(value: $sstMaxValue, in: 32...86) { _ in
                        updateSSTLayer()
                    }
                    Text("\(Int(sstMaxValue))°F")
                }
            }
            .padding()
        }
    }

    private func setupOceanLayers() {
        // Add SST layer
        addSSTLayer()

        // Add chlorophyll layer (optional)
        // addChlorophyllLayer()
    }

    private func addSSTLayer() {
        let timestamp = "2025-07-13T112950Z"
        let region = "ne_canyons"
        let dataset = "sst_composite"

        // Method 1: Using TiTiler direct endpoint (recommended)
        let cogURL = "\(cogBaseURL)/\(region)/\(dataset)/\(timestamp)_cog.tif"
        let tileURL = "\(tilerBaseURL)/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=\(cogURL)&rescale=\(sstMinValue),\(sstMaxValue)&colormap_name=sst_high_contrast&resampling=bilinear"

        // Method 2: Using structured path endpoint (alternative)
        // let tileURL = "\(tilerBaseURL)/tiles/\(dataset)/\(region)/\(timestamp)/{z}/{x}/{y}.png?min=\(sstMinValue)&max=\(sstMaxValue)"

        // Method 3: Using direct URL endpoint (alternative)
        // let tileURL = "\(tilerBaseURL)/tiles/{z}/{x}/{y}.png?url=\(cogURL)&min=\(sstMinValue)&max=\(sstMaxValue)&dataset=sst"

        // Create raster source
        var sstSource = RasterSource(id: "sst-source")
        sstSource.tiles = [tileURL]
        sstSource.tileSize = 256
        sstSource.minzoom = 3
        sstSource.maxzoom = 12

        // Create raster layer
        var sstLayer = RasterLayer(id: "sst-layer", source: "sst-source")
        sstLayer.rasterOpacity = .constant(0.8)

        // Add to map
        try? map.mapboxMap.addSource(sstSource)
        try? map.mapboxMap.addLayer(sstLayer)
    }

    private func updateSSTLayer() {
        // Remove existing layer and source
        try? map.mapboxMap.removeLayer(withId: "sst-layer")
        try? map.mapboxMap.removeSource(withId: "sst-source")

        // Add updated layer
        addSSTLayer()
    }

    private func addChlorophyllLayer() {
        let timestamp = "2025-07-13T112950Z"
        let region = "ne_canyons"
        let dataset = "chlor_a"

        let cogURL = "\(cogBaseURL)/\(region)/\(dataset)/\(timestamp)_cog.tif"
        let tileURL = "\(tilerBaseURL)/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=\(cogURL)&rescale=0.1,30&colormap_name=viridis&resampling=bilinear"

        var chlorSource = RasterSource(id: "chlor-source")
        chlorSource.tiles = [tileURL]
        chlorSource.tileSize = 256
        chlorSource.minzoom = 3
        chlorSource.maxzoom = 12

        var chlorLayer = RasterLayer(id: "chlor-layer", source: "chlor-source")
        chlorLayer.rasterOpacity = .constant(0.7)

        try? map.mapboxMap.addSource(chlorSource)
        try? map.mapboxMap.addLayer(chlorLayer)
    }
}
```

### Advanced Implementation with Multiple Datasets

```swift
import SwiftUI
import MapboxMaps

struct MultiLayerOceanMapView: View {
    @State private var map = Map()
    @State private var activeDataset: OceanDataset = .sst
    @State private var sstRange: ClosedRange<Double> = 32.0...86.0
    @State private var chlorRange: ClosedRange<Double> = 0.1...30.0

    private let tilerBaseURL = "http://localhost:8001"
    private let cogBaseURL = "https://data.saltyoffshore.com"

    enum OceanDataset: String, CaseIterable {
        case sst = "sst_composite"
        case chlorophyll = "chlor_a"

        var displayName: String {
            switch self {
            case .sst: return "Sea Surface Temperature"
            case .chlorophyll: return "Chlorophyll-a"
            }
        }

        var colormap: String {
            switch self {
            case .sst: return "sst_high_contrast"
            case .chlorophyll: return "viridis"
            }
        }

        var defaultRange: ClosedRange<Double> {
            switch self {
            case .sst: return 32.0...86.0
            case .chlorophyll: return 0.1...30.0
            }
        }
    }

    var body: some View {
        VStack {
            // Map view
            MapReader { proxy in
                Map(map: map)
                    .onAppear {
                        setupInitialLayer()
                    }
            }

            // Controls
            VStack(spacing: 16) {
                // Dataset selector
                Picker("Dataset", selection: $activeDataset) {
                    ForEach(OceanDataset.allCases, id: \.self) { dataset in
                        Text(dataset.displayName).tag(dataset)
                    }
                }
                .pickerStyle(SegmentedPickerStyle())
                .onChange(of: activeDataset) { _ in
                    updateActiveLayer()
                }

                // Range controls
                if activeDataset == .sst {
                    VStack {
                        Text("SST Range: \(Int(sstRange.lowerBound))°F - \(Int(sstRange.upperBound))°F")
                        RangeSlider(range: $sstRange, bounds: 32.0...86.0) {
                            updateActiveLayer()
                        }
                    }
                } else {
                    VStack {
                        Text("Chlorophyll Range: \(String(format: "%.1f", chlorRange.lowerBound)) - \(String(format: "%.1f", chlorRange.upperBound)) mg/m³")
                        RangeSlider(range: $chlorRange, bounds: 0.1...30.0) {
                            updateActiveLayer()
                        }
                    }
                }
            }
            .padding()
        }
    }

    private func setupInitialLayer() {
        updateActiveLayer()
    }

    private func updateActiveLayer() {
        // Remove existing layers
        try? map.mapboxMap.removeLayer(withId: "ocean-layer")
        try? map.mapboxMap.removeSource(withId: "ocean-source")

        let timestamp = "2025-07-13T112950Z"
        let region = "ne_canyons"
        let dataset = activeDataset.rawValue

        let cogURL = "\(cogBaseURL)/\(region)/\(dataset)/\(timestamp)_cog.tif"

        let range = activeDataset == .sst ? sstRange : chlorRange
        let tileURL = "\(tilerBaseURL)/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=\(cogURL)&rescale=\(range.lowerBound),\(range.upperBound)&colormap_name=\(activeDataset.colormap)&resampling=bilinear"

        var source = RasterSource(id: "ocean-source")
        source.tiles = [tileURL]
        source.tileSize = 256
        source.minzoom = 3
        source.maxzoom = 12

        var layer = RasterLayer(id: "ocean-layer", source: "ocean-source")
        layer.rasterOpacity = .constant(0.8)

        try? map.mapboxMap.addSource(source)
        try? map.mapboxMap.addLayer(layer)
    }
}

// Custom range slider component
struct RangeSlider: View {
    @Binding var range: ClosedRange<Double>
    let bounds: ClosedRange<Double>
    let onEditingChanged: () -> Void

    var body: some View {
        VStack {
            HStack {
                Slider(value: Binding(
                    get: { range.lowerBound },
                    set: { newValue in
                        range = newValue...min(range.upperBound, bounds.upperBound)
                    }
                ), in: bounds, onEditingChanged: { _ in onEditingChanged() })

                Slider(value: Binding(
                    get: { range.upperBound },
                    set: { newValue in
                        range = max(range.lowerBound, bounds.lowerBound)...newValue
                    }
                ), in: bounds, onEditingChanged: { _ in onEditingChanged() })
            }
        }
    }
}
```

### Key Implementation Notes

1. **URL Encoding**: Ensure COG URLs are properly URL-encoded when passed as parameters
2. **Tile Size**: Use 256px tiles for optimal performance with Mapbox
3. **Zoom Levels**: Set appropriate min/max zoom levels (3-12 recommended for ocean data)
4. **Opacity**: Use raster opacity for layer blending
5. **Dynamic Updates**: Remove and re-add layers when parameters change
6. **Error Handling**: Implement proper error handling for network requests

### Environment Configuration

For production, use environment variables:

```swift
private let tilerBaseURL = ProcessInfo.processInfo.environment["TILER_BASE_URL"] ?? "http://localhost:8001"
private let cogBaseURL = ProcessInfo.processInfo.environment["COG_BASE_URL"] ?? "https://data.saltyoffshore.com"
```

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
