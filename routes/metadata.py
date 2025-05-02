from fastapi import APIRouter, HTTPException

router = APIRouter()

# Dataset default ranges (extend as needed)
DATASET_RANGES = {
    "sst": {"min": -2.0, "max": 35.0},
    "chlorophyll": {"min": 0.01, "max": 30.0},
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