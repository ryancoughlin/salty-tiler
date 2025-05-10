#!/usr/bin/env python
"""
Start script for Salty Tiler - launches both:
1. Static file server for COGs (port 8000)
2. TiTiler API (port 8001)
"""
import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

def start_static_server():
    """Start a simple HTTP server to serve the static COG files."""
    print("🌐 Starting static file server on port 8000...")
    try:
        subprocess.run(
            [sys.executable, "-m", "http.server", "8000"],
            check=True,
        )
    except KeyboardInterrupt:
        print("💤 Static server stopped")

def start_api_server():
    """Start the TiTiler FastAPI server."""
    print("🚀 Starting TiTiler API on port 8001...")
    try:
        # Use uvicorn directly to avoid double-launching from app.py
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
            check=True,
        )
    except KeyboardInterrupt:
        print("💤 API server stopped")

def check_cogs_dir():
    """Check if the cogs directory exists and has files."""
    cogs_dir = Path("cogs")
    if not cogs_dir.exists():
        print("⚠️ cogs directory not found. Creating empty directory...")
        cogs_dir.mkdir(exist_ok=True)
        return False
    
    tif_files = list(cogs_dir.glob("*.tif"))
    if not tif_files:
        print("⚠️ No GeoTIFF files found in cogs directory.")
        print("ℹ️ You may need to run convert_all_nc_to_cog.py first.")
        return False
    
    print(f"🗺️ Found {len(tif_files)} GeoTIFF files in cogs directory.")
    return True

def main():
    """Main function to start both servers in separate threads."""
    print("🌊 Salty Tiler - Starting services")
    
    # Check for COGs
    has_cogs = check_cogs_dir()
    
    # Start the static server in a separate thread
    static_thread = threading.Thread(target=start_static_server, daemon=True)
    static_thread.start()
    
    # Give the static server a moment to start
    time.sleep(1)
    
    # Open browser tabs if COGs exist
    if has_cogs:
        # Open the API docs
        webbrowser.open("http://localhost:8001/docs")
    
    # Start the API server in the main thread
    start_api_server()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Shutting down all services...")
        sys.exit(0) 