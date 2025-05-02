"""
Batch convert all NetCDF files in a folder to GeoTIFFs in Fahrenheit and COGs with overviews for zooms 6–11.
- Processes only variables: 'sea_surface_temperature', 'analysed_sst', 'chlor_a'.
- Converts C/K to F if units are explicit ('celsius', 'kelvin', 'degree_C').
- Output COGs are written flat to ./cogs/.
- Uses xarray for variable/unit inspection, rasterio for GeoTIFF, and subprocess for GDAL COG/overviews.
- Logs each step clearly, including CRS used and skipped variables.

Usage:
    python convert_all_nc_to_cog.py

Requirements:
    - xarray
    - rasterio
    - gdal_translate, gdaladdo (CLI)
"""
import os
import subprocess
import numpy as np
import xarray as xr
import rasterio
from rasterio.transform import from_origin
import re
from enum import Enum
from typing import TypedDict
import h5py

# --- CONFIG ---
SRC_DIR = "raw_netcdf/"      # Input directory containing .nc files
DST_DIR = "cogs/"            # Output directory for COGs
ZOOM_OVERVIEWS = [2, 4, 8, 16, 32]  # For zooms 6–11
ALLOWED_VARS = {"sea_surface_temperature", "analysed_sst", "chlor_a"}
SINGLETON_DIMS = ["time", "depth", "altitude", "level"]  # Squeeze these if present
PREFERRED_SUBDATASETS = ["sea_surface_temperature", "analysed_sst", "chlor_a"]
NODATA_VALUE = -9999.0
# --- END CONFIG ---

class GeoreferenceType(str, Enum):
    METADATA_BOUNDS = "metadata_bounds"      # Use geospatial_*_min/max from metadata
    ORIGIN_PIXEL_SIZE = "origin_pixel_size"  # Use Origin + Pixel Size
    TWO_D_COORDS = "two_d_coords"            # Use 2D lat/lon arrays (not implemented)
    PROJ4_STRING = "proj4_string"            # Use proj4 string from metadata (not implemented)

class DatasetConfig(TypedDict):
    crs: str
    georef_type: GeoreferenceType

# Explicit config: key by dataset name or file pattern
DATASET_CONFIG: dict[str, DatasetConfig] = {
    "ABI-GOES19": {
        "crs": "EPSG:4326",
        "georef_type": GeoreferenceType.METADATA_BOUNDS,
    },
    "LEO": {
        "crs": "EPSG:4326",
        "georef_type": GeoreferenceType.ORIGIN_PIXEL_SIZE,
    },
    # New VIIRS chlorophyll dataset in Web Mercator
    "VIIRS_CHLOR_A": {
        "crs": "EPSG:3857",  # Web Mercator
        "georef_type": GeoreferenceType.ORIGIN_PIXEL_SIZE,
    },
}

def convert_to_fahrenheit(data: np.ndarray, units: str) -> np.ndarray:
    """Convert data from C or K to F. Fail if units are not recognized."""
    u = units.lower()
    if u in ("kelvin",):
        return (data - 273.15) * 9/5 + 32
    elif u in ("celsius", "degree_c"):
        return data * 9/5 + 32
    else:
        raise ValueError(f"Unrecognized units: {units}")

# Dataset type config for scalable, modular processing
DATASET_TYPE_CONFIG = {
    "sst": {
        "variables": ["sea_surface_temperature", "analysed_sst"],
        "allowed_units": ["kelvin", "celsius", "degree_c"],
        "output_units": "F",
        "convert": convert_to_fahrenheit,
    },
    "chlorophyll": {
        "variables": ["chlor_a"],
        "allowed_units": ["mg m^-3"],
        "output_units": "mg/m^3",
        "convert": lambda data, units: data,  # No conversion
    },
    # Extend here for new types, e.g. water clarity
    # "clarity": { ... }
}

# Helper to extract dataset key from filename (customize as needed)
def get_dataset_key(nc_path: str) -> str:
    fname = os.path.basename(nc_path)
    if "ABI-GOES19" in fname:
        return "ABI-GOES19"
    if "LEO" in fname:
        return "LEO"
    if "VIIIRS_CHLOR_A" in fname or "VIIRS_CHLOR_A" in fname:
        return "VIIRS_CHLOR_A"
    raise RuntimeError(f"No dataset config for file: {fname}")

def list_nc_variables(nc_path: str) -> dict:
    """Return a dict of variable names and their units from a NetCDF file."""
    with xr.open_dataset(nc_path) as ds:
        return {v: ds[v].attrs.get("units", "") for v in ds.data_vars}

def get_crs(ds, var) -> str:
    """
    Extract CRS for a variable from common sources.
    Supports:
      - Variable-level 'crs' attribute
      - Dataset-level 'crs' attribute
      - CF grid_mapping with 'crs_wkt' or 'spatial_ref'
      - Explicit mapping: grid_mapping_name=latitude_longitude and reference_ellipsoid_name/geographic_crs_name=WGS84 → EPSG:4326
    Fails if not found.
    """
    # 1. Variable-level CRS
    if "crs" in ds[var].attrs:
        print(f"🗺️  CRS from variable attribute: {ds[var].attrs['crs']}")
        return ds[var].attrs["crs"]
    # 2. Dataset-level CRS
    if "crs" in ds.attrs:
        print(f"🗺️  CRS from global attribute: {ds.attrs['crs']}")
        return ds.attrs["crs"]
    # 3. CF grid_mapping
    grid_mapping = ds[var].attrs.get("grid_mapping")
    if grid_mapping and grid_mapping in ds.variables:
        gm = ds[grid_mapping]
        if "crs_wkt" in gm.attrs:
            print(f"🗺️  CRS from crs_wkt: {gm.attrs['crs_wkt']}")
            return gm.attrs["crs_wkt"]
        if "spatial_ref" in gm.attrs:
            print(f"🗺️  CRS from spatial_ref: {gm.attrs['spatial_ref']}")
            return gm.attrs["spatial_ref"]
        # Explicit mapping for latitude_longitude + WGS84
        grid_mapping_name = gm.attrs.get("grid_mapping_name")
        ellipsoid = gm.attrs.get("reference_ellipsoid_name")
        geo_crs = gm.attrs.get("geographic_crs_name")
        if (
            grid_mapping_name == "latitude_longitude" and
            (ellipsoid == "WGS84" or geo_crs == "WGS84")
        ):
            print("🗺️  CRS mapped to EPSG:4326 (latitude_longitude + WGS84)")
            return "EPSG:4326"
    # 4. Try global attrs for explicit mapping
    grid_mapping_name = ds.attrs.get("grid_mapping_name")
    ellipsoid = ds.attrs.get("grid_mapping_reference_ellipsoid_name")
    geo_crs = ds.attrs.get("geographic_crs_name")
    if (
        grid_mapping_name == "latitude_longitude" and
        (ellipsoid == "WGS84" or geo_crs == "WGS84")
    ):
        print("🗺️  CRS mapped to EPSG:4326 (global latitude_longitude + WGS84)")
        return "EPSG:4326"
    raise ValueError(f"No CRS found for variable '{var}'")

def write_geotiff(data: np.ndarray, profile: dict, out_path: str):
    """Write data to GeoTIFF using rasterio."""
    profile = profile.copy()
    profile.update(
        dtype=rasterio.float32,
        nodata=-9999,
        driver="GTiff",
        compress="DEFLATE",
    )
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(data.astype(rasterio.float32), 1)

def create_cog_and_overviews(geotiff_path: str, cog_path: str):
    """Create COG without internal overviews. Uses only COG driver options (see https://gdal.org/drivers/raster/cog.html)."""
    print(f"\U0001F3D7️  [COG] gdal_translate {geotiff_path} -> {cog_path} (no internal overviews)")
    subprocess.run([
        "gdal_translate", "-of", "COG",
        "-co", "COMPRESS=DEFLATE",
        "-co", "PREDICTOR=2",
        "-co", "BLOCKSIZE=512",
        "-co", "OVERVIEWS=NONE",
        geotiff_path, cog_path
    ], check=True)
    print(f"✅ Done: {cog_path}")

def debug_crs_info(ds, var):
    print(f"--- CRS Debug for variable '{var}' ---")
    # Print variable-level attributes
    print(f"Variable attrs: {ds[var].attrs}")
    # Print global attributes
    print(f"Global attrs: {ds.attrs}")
    # If grid_mapping, print referenced variable's attrs
    grid_mapping = ds[var].attrs.get("grid_mapping")
    if grid_mapping and grid_mapping in ds.variables:
        print(f"grid_mapping '{grid_mapping}' attrs: {ds[grid_mapping].attrs}")
    print("--- End CRS Debug ---")

def squeeze_singleton_dims(da, dims_to_squeeze):
    """Squeeze specified singleton dimensions from an xarray DataArray."""
    for dim in dims_to_squeeze:
        if dim in da.dims and da.sizes[dim] == 1:
            da = da.isel({dim: 0})
    return da

def get_gdalinfo_metadata(nc_path, subdataset=None):
    path = f'NETCDF:"{nc_path}":{subdataset}' if subdataset else nc_path
    cmd = ["gdalinfo", path]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout

def parse_origin_pixel_size(gdalinfo_output):
    origin = re.search(r"Origin = \(([^,]+),([^)]+)\)", gdalinfo_output)
    pixel = re.search(r"Pixel Size = \(([^,]+),([^)]+)\)", gdalinfo_output)
    if origin and pixel:
        x0, y0 = float(origin.group(1)), float(origin.group(2))
        px, py = float(pixel.group(1)), float(pixel.group(2))
        return x0, y0, px, py
    return None

def parse_size(gdalinfo_output):
    size = re.search(r"Size is (\d+), (\d+)", gdalinfo_output)
    if size:
        return int(size.group(1)), int(size.group(2))
    return None

def parse_bounds_from_metadata(gdalinfo_output):
    attrs = {}
    for key in ["geospatial_lon_min", "geospatial_lon_max", "geospatial_lat_min", "geospatial_lat_max"]:
        match = re.search(rf"{key}=([\-\d.]+)", gdalinfo_output)
        if match:
            attrs[key] = float(match.group(1))
    if len(attrs) == 4:
        return attrs["geospatial_lon_min"], attrs["geospatial_lat_min"], attrs["geospatial_lon_max"], attrs["geospatial_lat_max"]
    return None

def choose_subdataset(gdalinfo_output, preferred_list):
    for name in preferred_list:
        for line in gdalinfo_output.splitlines():
            if f':{name}"' in line or f':{name} ' in line:
                return name
    return None

def get_transform_and_crs_config(nc_path, config: DatasetConfig):
    gdalinfo_out = get_gdalinfo_metadata(nc_path)
    subdataset = choose_subdataset(gdalinfo_out, PREFERRED_SUBDATASETS)
    if subdataset:
        gdalinfo_out = get_gdalinfo_metadata(nc_path, subdataset)
    size = parse_size(gdalinfo_out)
    if config["georef_type"] == GeoreferenceType.ORIGIN_PIXEL_SIZE:
        origin_px = parse_origin_pixel_size(gdalinfo_out)
        if not (origin_px and size):
            raise RuntimeError(f"Missing origin/pixel size for {nc_path}")
        x0, y0, px, py = origin_px
        width, height = size
        from rasterio.transform import from_origin
        # Always use positive py for transform
        transform = from_origin(x0, y0, abs(px), abs(py))
        xmin = x0
        xmax = x0 + width * px
        ymax = y0
        ymin = y0 + height * py
        bounds_calc = (xmin, ymin, xmax, ymax)
        method = "origin+pixel_size"
        flip_y = py < 0
        print(f"[GEO] Using origin/pixel size: origin=({x0},{y0}), px={px}, py={py}, size=({width},{height})")
        print(f"[GEO] Calculated bounds: {bounds_calc}")
        print(f"[GEO] CRS: {config['crs']}")
        return transform, config["crs"], subdataset, bounds_calc, method, flip_y
    elif config["georef_type"] == GeoreferenceType.METADATA_BOUNDS:
        bounds = parse_bounds_from_metadata(gdalinfo_out)
        if not (bounds and size):
            raise RuntimeError(f"Missing metadata bounds for {nc_path}")
        xmin, ymin, xmax, ymax = bounds
        width, height = size
        from rasterio.transform import from_bounds
        transform = from_bounds(xmin, ymin, xmax, ymax, width, height)
        method = "metadata_bounds"
        print(f"[GEO] Using metadata bounds: {bounds}")
        print(f"[GEO] CRS: {config['crs']}")
        return transform, config["crs"], subdataset, bounds, method, False
    else:
        raise NotImplementedError(f"Georeference type {config['georef_type']} not implemented")

def is_latitude_ascending(ds, lat_name="latitude"):
    lat = ds[lat_name].values
    return lat[0] < lat[-1]

def build_overviews(cog_path):
    print(f"🏗️  [OVR] gdaladdo -r cubicspline {cog_path} 2 4 8 16 32")
    subprocess.run([
        "gdaladdo", "-r", "cubicspline", cog_path, "2", "4", "8", "16", "32"
    ], check=True)
    print(f"✅ Overviews built: {cog_path}")

def upsample_geotiff(input_path, output_path, scale_factor=2):
    """Upsample the GeoTIFF to a finer grid using cubicspline interpolation."""
    if os.path.exists(output_path):
        print(f"🗑️  Removing existing upsampled file: {output_path}")
        os.remove(output_path)
    with rasterio.open(input_path) as src:
        orig_res_x, orig_res_y = src.res[0], src.res[1]
    target_res_x = orig_res_x / scale_factor
    target_res_y = abs(orig_res_y) / scale_factor
    print(f"🔼 Upsampling {input_path} by {scale_factor}x to resolution {target_res_x}, {target_res_y} (cubicspline)")
    subprocess.run([
        "gdalwarp",
        "-overwrite",
        "-tr", str(target_res_x), str(target_res_y),
        "-r", "cubicspline",
        input_path, output_path
    ], check=True)
    print(f"✅ Upsampled: {output_path}")

def open_netcdf_h5netcdf(path_str: str) -> xr.Dataset:
    """Try to open with xarray using h5netcdf engine."""
    return xr.open_dataset(path_str, engine='h5netcdf')

def read_chlor_a_h5netcdf_phony(path_str: str):
    import h5netcdf
    import numpy as np
    with h5netcdf.File(path_str, mode="r", phony_dims="sort") as f:
        arr = f.variables['chlor_a'][:]
        arr = np.squeeze(arr)
        return arr

def open_coastwatch_netcdf(path: str) -> xr.Dataset:
    """Open CoastWatch NetCDFs robustly: netcdf4 engine, no decoding, then decode_cf."""
    ds = xr.open_dataset(
        path,
        engine="netcdf4",
        decode_cf=False,
        decode_times=False,
        decode_coords=False,
        mask_and_scale=False,
        chunks=None,
    ).load()
    ds = xr.decode_cf(ds)
    return ds

def open_netcdf_subdataset_rasterio(nc_path: str, var: str):
    """Open a NetCDF subdataset (e.g., chlor_a) with rasterio and return (data, profile)."""
    subdataset_path = f'NETCDF:"{nc_path}":{var}'
    with rasterio.open(subdataset_path) as src:
        data = src.read(1)
        profile = src.profile.copy()
    return data, profile

def get_dataset_type(dataset_key: str) -> str:
    if dataset_key in ("ABI-GOES19", "LEO"):
        return "sst"
    if dataset_key == "VIIRS_CHLOR_A":
        return "chlorophyll"
    # Add more mappings as needed
    raise RuntimeError(f"Unknown dataset type for key: {dataset_key}")

def process_nc_file(nc_path: str):
    print(f"\n🏁 Processing {nc_path}")
    dataset_key = get_dataset_key(nc_path)
    if dataset_key not in DATASET_CONFIG:
        raise RuntimeError(f"No config for dataset: {dataset_key}")
    config = DATASET_CONFIG[dataset_key]
    dataset_type = get_dataset_type(dataset_key)
    type_cfg = DATASET_TYPE_CONFIG[dataset_type]
    variables = list_nc_variables(nc_path)
    print(f"🔍 Variables found: {variables}")
    # CoastWatch/VIIRS chlorophyll: rasterio subdataset loader
    if dataset_key == "VIIRS_CHLOR_A":
        for var in type_cfg["variables"]:
            if var not in variables:
                continue
            units = variables[var]
            print(f"🧪 Processing variable: {var} (units: {units}) [rasterio subdataset]")
            data, profile = open_netcdf_subdataset_rasterio(nc_path, var)
            data = type_cfg["convert"](data, units)
            data = np.where(np.isnan(data), NODATA_VALUE, data)
            profile.update(nodata=NODATA_VALUE, compress="DEFLATE")
            date = os.path.splitext(os.path.basename(nc_path))[0].split("_")[-1]
            geotiff_path = os.path.join(DST_DIR, f"{var}_{date}_{type_cfg['output_units'].replace('/', '')}.tif")
            cog_path = os.path.join(DST_DIR, f"{var}_{date}_{type_cfg['output_units'].replace('/', '')}_cog.tif")
            print(f"💾 Writing GeoTIFF: {geotiff_path}")
            write_geotiff(data, profile, geotiff_path)
            upsample_geotiff(geotiff_path, geotiff_path.replace('.tif', '_upsampled.tif'), scale_factor=2)
            create_cog_and_overviews(geotiff_path.replace('.tif', '_upsampled.tif'), cog_path)
            build_overviews(cog_path)
            print(f"✅ Done: {cog_path}")
        return
    # Generic xarray loader for all other datasets
    with xr.open_dataset(nc_path) as ds:
        for var in type_cfg["variables"]:
            if var not in variables:
                continue
            units = variables[var]
            print(f"🧪 Processing variable: {var} (units: {units})")
            debug_crs_info(ds, var)
            da = ds[var]
            print(f"🔹 Original shape for {var}: {da.shape}, dims: {da.dims}")
            da_squeezed = squeeze_singleton_dims(da, SINGLETON_DIMS)
            print(f"🔹 Squeezed shape for {var}: {da_squeezed.shape}, dims: {da_squeezed.dims}")
            da_squeezed.load()
            data = da_squeezed.values
            data = type_cfg["convert"](data, units)
            try:
                transform, crs, subdataset, bounds, method, _ = get_transform_and_crs_config(nc_path, config)
                print(f"🗺️  CRS for {var}: {crs} (method: {method})")
            except Exception as e:
                print(f"❌ Skipping {var}: {e}")
                continue
            if config["georef_type"] == GeoreferenceType.ORIGIN_PIXEL_SIZE:
                lat_dim = [d for d in da_squeezed.dims if "lat" in d or "latitude" in d]
                lat_name = lat_dim[0] if lat_dim else da_squeezed.dims[-2]
                if is_latitude_ascending(ds, lat_name):
                    print(f"↕️  Flipping data vertically to match north-up orientation (lat ascending in data).")
                    data = np.flipud(data)
            data = np.where(np.isnan(data), NODATA_VALUE, data)
            profile = {
                "height": data.shape[-2],
                "width": data.shape[-1],
                "count": 1,
                "crs": crs,
                "transform": transform,
                "nodata": NODATA_VALUE,
            }
            date = os.path.splitext(os.path.basename(nc_path))[0].split("_")[-1]
            geotiff_path = os.path.join(DST_DIR, f"{var}_{date}_{type_cfg['output_units'].replace('/', '')}.tif")
            cog_path = os.path.join(DST_DIR, f"{var}_{date}_{type_cfg['output_units'].replace('/', '')}_cog.tif")
            upsampled_path = geotiff_path.replace('.tif', '_upsampled.tif')
            print(f"💾 Writing GeoTIFF: {geotiff_path}")
            write_geotiff(data, profile, geotiff_path)
            upsample_geotiff(geotiff_path, upsampled_path, scale_factor=2)
            create_cog_and_overviews(upsampled_path, cog_path)
            build_overviews(cog_path)
            print(f"✅ Done: {cog_path}")

def main():
    os.makedirs(DST_DIR, exist_ok=True)
    for fname in os.listdir(SRC_DIR):
        if fname.endswith(".nc"):
            process_nc_file(os.path.join(SRC_DIR, fname))

if __name__ == "__main__":
    main() 
    main() 