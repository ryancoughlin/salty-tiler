from pydantic import BaseModel, Field
from typing import Dict

class GeoTIFFInfo(BaseModel):
    """
    Information about a GeoTIFF/COG layer for a given entry.
    """
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    path: str = Field(..., description="Local path to the COG file")

class EntryLayers(BaseModel):
    """
    Layers available for an entry. Extend as needed for more layer types.
    """
    geotiff: GeoTIFFInfo

class Entry(BaseModel):
    """
    Entry metadata as returned from Supabase (or mock).
    """
    uuid: str
    dataset_id: str
    region: str
    layers: EntryLayers 