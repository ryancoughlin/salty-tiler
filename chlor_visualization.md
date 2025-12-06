# Chlorophyll Visualization Technique: High-Detail Log10 Rendering

## Overview

The chlorophyll visualization achieves exceptional detail in the critical low-chlorophyll range (0.01-1.0 mg/m³) while maintaining full coverage up to 8.0 mg/m³. This technique uses **log10 normalization with color stops positioned in logarithmic space** to maximize visual resolution where it matters most for offshore fishing.

## Core Technique: Log10 Normalization with Positioned Color Stops

### Why Log10?

Chlorophyll concentrations in ocean water follow a logarithmic distribution:
- **Low range (0.01-1.0 mg/m³)**: Ultra-clear Gulf Stream to productive offshore waters - **critical for fishing**
- **High range (1.0-8.0 mg/m³)**: Coastal blooms and turbid water - less detail needed

Linear scaling would waste color resolution on high values. Log10 compression:
- **Expands** the low range (0.01-1.0) → more color steps per unit
- **Compresses** the high range (1.0-8.0) → fewer steps needed
- **Result**: Maximum visual detail where fishermen need it most

### Implementation Details

#### 1. Log10 Range Calculation

```python
log_min = math.log10(0.01)  # -2.0
log_max = math.log10(8.0)   # ~0.903
log_range = log_max - log_min  # ~2.903
```

#### 2. Color Stop Positioning in Log10 Space

Color stops are defined in **linear mg/m³ values** but positioned in **log10-normalized space**:

```python
color_positions = []
for value, color in config.color_stops:
    log_value = math.log10(value)  # Convert to log10
    position = (log_value - log_min) / log_range  # Normalize to 0-1
    color_positions.append((position, color))
```

**Example**: Stop at 0.1 mg/m³
- `log10(0.1) = -1.0`
- Position: `(-1.0 - (-2.0)) / 2.903 = 0.344` (34.4% through colormap)

**Example**: Stop at 1.0 mg/m³
- `log10(1.0) = 0.0`
- Position: `(0.0 - (-2.0)) / 2.903 = 0.689` (68.9% through colormap)

#### 3. High-Resolution Colormap

```python
continuous_cmap = LinearSegmentedColormap.from_list(
    'chlorophyll_log10',
    color_positions,
    N=2048  # High resolution for smooth gradients
)
```

The `N=2048` parameter creates 2048 color steps, ensuring smooth interpolation between the 19 color stops.

#### 4. Matplotlib LogNorm Application

```python
norm = LogNorm(vmin=0.01, vmax=8.0)
```

`LogNorm` applies log10 transformation to the **data values** before mapping to the colormap. Combined with log10-positioned color stops, this creates a **double log10 effect**:
- Data values → log10 → normalized (0-1)
- Color stops already positioned in log10 space
- Perfect alignment for maximum detail

## Color Stop Configuration

### 19 Color Stops (0.01-8.0 mg/m³)

```python
CHLOROPHYLL_LOG10_STOPS = [
    (0.01, '#E040E0'),  # Ultra-clear Gulf Stream
    (0.02, '#9966CC'),  # Purple transition
    (0.03, '#6633CC'),  # Purple-blue blend
    (0.05, '#0D1F6D'),  # Deep indigo (open ocean)
    (0.07, '#1E3A8A'),  # Deep blue
    (0.10, '#1E40AF'),  # Strong blue (oligotrophic)
    (0.20, '#2196F3'),  # Professional blue
    (0.30, '#3B82F6'),  # Light blue
    (0.50, '#00BCD4'),  # Cyan (transition)
    (0.70, '#00ACC1'),  # Deeper cyan
    (1.00, '#00897B'),  # Teal-green (offshore)
    (1.50, '#26A69A'),  # Teal (productive)
    (2.00, '#4CAF50'),  # Green (coastal)
    (3.00, '#66BB6A'),  # Bright green
    (4.00, '#9CCC65'),  # Yellow-green
    (5.00, '#C0CA33'),  # Lime
    (6.00, '#FDD835'),  # Yellow (blooms)
    (7.00, '#FFB300'),  # Amber-orange
    (8.00, '#F57C00'),  # Deep orange (max)
]
```

### Stop Distribution Analysis

**Low range (0.01-1.0 mg/m³)**: 11 stops (58% of stops, 34% of range)
- Maximum detail where needed
- Each 0.1 mg/m³ increment gets distinct color

**High range (1.0-8.0 mg/m³)**: 8 stops (42% of stops, 66% of range)
- Adequate detail for coastal/bloom conditions
- Coarser steps acceptable

## Rendering Pipeline

### Complete Flow

```
Raw Data (chlor_a)
    ↓
Clamp to [0.01, 8.0] (preprocessing)
    ↓
LogNorm(vmin=0.01, vmax=8.0) → log10 transform
    ↓
Normalize to [0, 1] range
    ↓
Map to colormap (2048 steps, log10-positioned stops)
    ↓
Gouraud shading (smooth interpolation)
    ↓
Final visualization
```

### Key Parameters

- **Normalization**: `LogNorm(vmin=0.01, vmax=8.0)`
- **Colormap resolution**: `N=2048`
- **Shading**: `gouraud` (smooth gradient interpolation)
- **Rasterization**: `True` (memory efficiency)

## Replicating in TiTiler

### 1. Log10 Expression

TiTiler uses expressions for data transformation:

```python
expression = "log10(clamp(chlor_a, 0.01, 8.0))"
```

This applies the same log10 transformation as Matplotlib's `LogNorm`.

### 2. Colormap with Log10-Positioned Stops

Create a colormap JSON with stops positioned in log10 space:

```python
def create_titiler_colormap():
    """Generate TiTiler colormap with log10-positioned stops."""
    log_min = math.log10(0.01)
    log_max = math.log10(8.0)
    log_range = log_max - log_min
    
    stops = []
    for value, color in CHLOROPHYLL_LOG10_STOPS:
        log_value = math.log10(value)
        position = (log_value - log_min) / log_range
        stops.append({
            "value": position,  # Position in normalized log10 space (0-1)
            "color": color
        })
    
    return {
        "type": "linear",
        "stops": stops
    }
```

### 3. TiTiler Request Configuration

```python
# TiTiler render request
params = {
    "expression": "log10(clamp(chlor_a, 0.01, 8.0))",
    "colormap": "chlorophyll_log10",  # Custom colormap name
    "rescale": "0,1",  # Normalized log10 range
    "colormap_type": "linear"
}
```

### 4. Colormap Registration

Register the custom colormap with TiTiler:

```python
# In TiTiler configuration
custom_colormaps = {
    "chlorophyll_log10": {
        "type": "linear",
        "stops": [
            {"value": 0.0, "color": "#E040E0"},   # 0.01 mg/m³
            {"value": 0.344, "color": "#1E40AF"}, # 0.10 mg/m³
            {"value": 0.689, "color": "#00897B"}, # 1.00 mg/m³
            {"value": 1.0, "color": "#F57C00"}    # 8.00 mg/m³
            # ... all 19 stops
        ]
    }
}
```

### 5. Complete TiTiler Example

```python
import requests
import math

# Calculate log10 positions for all stops
log_min = math.log10(0.01)
log_max = math.log10(8.0)
log_range = log_max - log_min

stops = []
for value, color in CHLOROPHYLL_LOG10_STOPS:
    log_value = math.log10(value)
    position = (log_value - log_min) / log_range
    stops.append({"value": position, "color": color})

# TiTiler render endpoint
url = "https://your-titiler-server/cog/render"
params = {
    "url": "s3://bucket/path/to/chlorophyll.tif",
    "expression": "log10(clamp(chlor_a, 0.01, 8.0))",
    "rescale": f"{log_min},{log_max}",  # Actual log10 range
    "colormap": json.dumps({
        "type": "linear",
        "stops": stops
    }),
    "colormap_type": "linear"
}

response = requests.get(url, params=params)
```

## Key Insights for High Detail

### 1. Double Log10 Alignment

- **Data transformation**: `log10(data)` via LogNorm/expression
- **Color stop positioning**: Stops positioned in log10 space
- **Result**: Perfect alignment maximizes detail in low range

### 2. Stop Density Strategy

- **High density** (0.01-1.0): 11 stops for 1.0 mg/m³ range
- **Lower density** (1.0-8.0): 8 stops for 7.0 mg/m³ range
- **Rationale**: Fishermen need detail in clear water, not blooms

### 3. High-Resolution Interpolation

- `N=2048` colormap steps ensure smooth gradients
- Gouraud shading provides pixel-level smoothness
- No banding artifacts in critical low range

### 4. Range Clamping

- Pre-clamp to [0.01, 8.0] before log10
- Prevents log10(0) = -∞ issues
- Ensures consistent visualization bounds

## Performance Considerations

### Memory Efficiency

- **Rasterization**: `rasterized=True` reduces memory for large datasets
- **Array cleanup**: Explicit `del` statements prevent memory accumulation
- **Single materialization**: Data arrays materialized once, reused

### Rendering Quality

- **Gouraud shading**: Smooth interpolation without artifacts
- **High DPI**: 600 DPI for print-quality output
- **Transparent NaN**: `set_bad(alpha=0)` for clean backgrounds

## Comparison: Linear vs Log10

### Linear Scaling (Poor Detail)

```
0.01 → 0.0% position
0.10 → 1.2% position  (only 1.2% of colormap for critical range!)
1.00 → 12.4% position
8.00 → 100% position
```

**Problem**: 87.6% of colormap wasted on high values

### Log10 Scaling (Optimal Detail)

```
0.01 → 0.0% position
0.10 → 34.4% position  (34.4% of colormap for critical range!)
1.00 → 68.9% position
8.00 → 100% position
```

**Solution**: 68.9% of colormap dedicated to low range where detail matters

## Summary

The chlorophyll visualization achieves high detail through:

1. **Log10 normalization** of data values (0.01-8.0 mg/m³)
2. **Log10-positioned color stops** (19 stops, dense in low range)
3. **High-resolution colormap** (2048 steps for smooth gradients)
4. **Gouraud shading** (pixel-level smoothness)
5. **Strategic stop density** (more stops where detail is critical)

For TiTiler replication:
- Use `log10(clamp(var, 0.01, 8.0))` expression
- Create colormap with stops positioned in normalized log10 space
- Register as custom colormap with linear interpolation
- Use same 19 color stops for visual consistency

This technique can be applied to any variable with logarithmic distribution where low-range detail is critical.

