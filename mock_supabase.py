"""
Mock Supabase integration for testing and development.
Replace with real Supabase client in production.
"""
from typing import Dict, Any, Optional
from pathlib import Path

# Mock entries database - maps entry_id to entry data
MOCK_ENTRIES: Dict[str, Dict[str, Any]] = {
    "test-entry-1": {
        "id": "test-entry-1",
        "dataset_id": "sst",
        "region": "florida_keys",
        "layers": {
            "geotiff": {
                "path": "cogs/sea_surface_temperature_LEO-2025-05-01T000000Z_F_cog.tif",
                "date": "2025-05-01",
                "format": "COG"
            }
        }
    },
    "test-entry-2": {
        "id": "test-entry-2", 
        "dataset_id": "chlorophyll",
        "region": "global",
        "layers": {
            "geotiff": {
                "path": "cogs/chlor_a_2025-04-29T000000Z_mgm^3_cog.tif",
                "date": "2025-04-29",
                "format": "COG"
            }
        }
    }
}

def get_entry_by_id(entry_id: str) -> Optional[Dict[str, Any]]:
    """
    Mock function to get entry by ID.
    In production, this would query the Supabase entries table.
    """
    entry = MOCK_ENTRIES.get(entry_id)
    if entry:
        # Verify that the COG file actually exists
        cog_path = Path(entry["layers"]["geotiff"]["path"])
        if cog_path.exists():
            return entry
    return None

def list_entries() -> Dict[str, Dict[str, Any]]:
    """
    Mock function to list all entries.
    In production, this would query the Supabase entries table.
    """
    # Only return entries where the COG file exists
    valid_entries = {}
    for entry_id, entry in MOCK_ENTRIES.items():
        cog_path = Path(entry["layers"]["geotiff"]["path"])
        if cog_path.exists():
            valid_entries[entry_id] = entry
    return valid_entries 