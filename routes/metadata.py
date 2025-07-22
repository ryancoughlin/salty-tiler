from fastapi import APIRouter, HTTPException

router = APIRouter()

# Dataset default ranges (Fahrenheit for SST, original units for chlorophyll, PSU for salinity)
DATASET_RANGES = {
    "sst": {"min": 32.0, "max": 95.0},  # Fahrenheit range
    "chlorophyll": {"min": 0.01, "max": 20.0},  # Match Python app's SymLogNorm range
    "salinity": {"min": 28.0, "max": 37.5},  # PSU range
}

@router.get("/metadata/{dataset}/range")
def get_dataset_range(dataset: str):
    """
    Return min/max value range for a dataset (for slider bounds).
    """
    cfg = DATASET_RANGES.get(dataset)
    if not cfg:
        raise HTTPException(404, "Unknown dataset")
    return {"dataset": dataset, **cfg} 