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
from typing import Dict, Any

# Example hardcoded entries for testing
MOCK_ENTRIES: Dict[str, Dict[str, Any]] = {
    "test-entry-1": {
        "uuid": "test-entry-1",
        "dataset_id": "sst",
        "region": "keys",
        "layers": {
            "geotiff": {
                "date": "2025-05-01",
                "path": "cogs/sst_keys_2025-05-01.tif"
            }
        }
    },
    # Add more entries as needed
}

def get_entry_by_id(entry_id: str) -> Dict[str, Any]:
    """
    Retrieve entry by entry_id from the mock database.
    Replace with Supabase query in production.
    """
    return MOCK_ENTRIES.get(entry_id) 