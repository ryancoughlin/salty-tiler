from fastapi import FastAPI
from routes.metadata import router as metadata_router
from routes.tiles import router as tiles_router

# Main FastAPI app for tile serving
# - Loads custom palette at startup
# - Registers /metadata and /tiles endpoints
# - Modular, ready for real Supabase integration

app = FastAPI(
    title="Salty Tiler POC",
    description="Minimal, modular TiTiler API for ocean tiles with custom palette and Supabase entry lookup (mocked)",
    version="0.1.0",
)

# Register routers
app.include_router(metadata_router)
app.include_router(tiles_router) 