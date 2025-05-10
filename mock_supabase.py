"""
Mock Supabase entry lookup for local development/testing.
Replace with real Supabase client and queries for production.

Entry schema:
{
    "uuid": str,  # entry_id
    "dataset_id": str,
    "region": str,
    "layers": {
        "geotiff": {
            "date": str,  # YYYY-MM-DD
            "path": str   # local COG path
        }
    }
}
"""
from typing import Dict, Any, Optional
import os

# Example hardcoded entries for testing
# For development flexibility, look for COGs in the cogs directory to use in mocked entries
def _find_cog_file(dataset: str = "sst") -> Optional[str]:
    cogs_dir = "cogs"
    if not os.path.exists(cogs_dir):
        return None
    
    # Find a suitable COG file for the dataset
    for filename in os.listdir(cogs_dir):
        if filename.lower().endswith(".tif"):
            if dataset == "sst" and any(x in filename.lower() for x in ["sst", "temperature"]):
                return os.path.join(cogs_dir, filename)
            elif dataset == "chlorophyll" and any(x in filename.lower() for x in ["chlor", "chlorophyll"]):
                return os.path.join(cogs_dir, filename)
    
    # No specific match, return first TIF if any
    for filename in os.listdir(cogs_dir):
        if filename.lower().endswith(".tif"):
            return os.path.join(cogs_dir, filename)
            
    return None

# Dynamically find COG files for each dataset
sst_path = _find_cog_file("sst") or "cogs/sst_example.tif"
chlor_path = _find_cog_file("chlorophyll") or "cogs/chlor_example.tif"

MOCK_ENTRIES: Dict[str, Dict[str, Any]] = {
    "test-entry-1": {
        "uuid": "test-entry-1",
        "dataset_id": "sst",
        "region": "keys",
        "layers": {
            "geotiff": {
                "date": "2025-05-01",
                "path": sst_path
            }
        }
    },
    "test-entry-2": {
        "uuid": "test-entry-2",
        "dataset_id": "chlorophyll",
        "region": "gulf",
        "layers": {
            "geotiff": {
                "date": "2025-05-01",
                "path": chlor_path
            }
        }
    }
}

def get_entry_by_id(entry_id: str) -> Dict[str, Any]:
    """
    Retrieve entry by entry_id from the mock database.
    Replace with Supabase query in production.
    """
    return MOCK_ENTRIES.get(entry_id) 