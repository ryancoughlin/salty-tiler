#!/usr/bin/env python3
"""
Test script for external COG URL functionality
"""
import requests
import json
from urllib.parse import urljoin

# Test configuration
BASE_URL = "http://localhost:8001"
EXTERNAL_COG_URL = "https://data.saltyoffshore.com/ne_canyons/sst_composite/2025-07-13T070646Z_cog.tif"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")

def test_direct_url_endpoint():
    """Test the direct URL endpoint"""
    print("\n🔍 Testing direct URL endpoint...")
    try:
        params = {
            "url": EXTERNAL_COG_URL,
            "min": 32,
            "max": 86,
            "dataset": "sst"
        }
        response = requests.get(f"{BASE_URL}/tiles/6/12/20.png", params=params)
        
        if response.status_code == 200:
            print("✅ Direct URL endpoint works")
            print(f"   Content-Type: {response.headers.get('content-type')}")
            print(f"   Content-Length: {len(response.content)} bytes")
            print(f"   COG URL: {response.headers.get('X-COG-URL')}")
        else:
            print(f"❌ Direct URL endpoint failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Direct URL endpoint error: {e}")

def test_structured_endpoint():
    """Test the structured path endpoint"""
    print("\n🔍 Testing structured path endpoint...")
    try:
        params = {
            "min": 32,
            "max": 86,
            "base_url": "https://data.saltyoffshore.com"
        }
        response = requests.get(
            f"{BASE_URL}/tiles/sst_composite/ne_canyons/2025-07-13T070646Z/6/12/20.png", 
            params=params
        )
        
        if response.status_code == 200:
            print("✅ Structured path endpoint works")
            print(f"   Content-Type: {response.headers.get('content-type')}")
            print(f"   Content-Length: {len(response.content)} bytes")
            print(f"   COG URL: {response.headers.get('X-COG-URL')}")
        else:
            print(f"❌ Structured path endpoint failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Structured path endpoint error: {e}")

def test_metadata_endpoint():
    """Test the metadata endpoint"""
    print("\n🔍 Testing metadata endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/metadata/sst/range")
        
        if response.status_code == 200:
            print("✅ Metadata endpoint works")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Metadata endpoint failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Metadata endpoint error: {e}")

def test_titiler_direct():
    """Test TiTiler direct endpoint"""
    print("\n🔍 Testing TiTiler direct endpoint...")
    try:
        params = {
            "url": EXTERNAL_COG_URL,
            "rescale": "32,86",
            "colormap_name": "sst_high_contrast",
            "resampling": "bilinear"
        }
        response = requests.get(
            f"{BASE_URL}/cog/tiles/WebMercatorQuad/6/12/20.png", 
            params=params
        )
        
        if response.status_code == 200:
            print("✅ TiTiler direct endpoint works")
            print(f"   Content-Type: {response.headers.get('content-type')}")
            print(f"   Content-Length: {len(response.content)} bytes")
        else:
            print(f"❌ TiTiler direct endpoint failed: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ TiTiler direct endpoint error: {e}")

def main():
    """Run all tests"""
    print("🌊 Salty Tiler - External COG URL Tests")
    print("=" * 50)
    
    test_health_check()
    test_metadata_endpoint()
    test_direct_url_endpoint()
    test_structured_endpoint()
    test_titiler_direct()
    
    print("\n🎉 Test suite completed!")

if __name__ == "__main__":
    main() 