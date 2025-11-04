"""
Storage utilities for S3-compatible storage (AWS S3, DigitalOcean Spaces, etc.).

Provides functions to convert HTTP URLs to VSI paths for authenticated access
when credentials are configured.
"""
import os
from typing import Optional
from urllib.parse import urlparse

# Configure GDAL for S3-compatible endpoints
def configure_gdal_for_s3():
    """
    Configure GDAL environment variables for S3-compatible storage.
    
    This must be called before GDAL is initialized (before importing rasterio/titiler).
    For DigitalOcean Spaces and other S3-compatible services, GDAL needs the endpoint
    to be configured via environment variables.
    
    Supports both AWS_* and SPACES_* environment variables. Maps SPACES_* to AWS_* 
    for GDAL compatibility since GDAL expects AWS_* variables.
    
    GDAL's VSI S3 driver will use AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and
    AWS_S3_ENDPOINT from the environment when accessing /vsis3/ paths.
    """
    # Support DigitalOcean Spaces variables (SPACES_*) and map to AWS_* for GDAL
    spaces_key = os.getenv("SPACES_ACCESS_KEY_ID")
    spaces_secret = os.getenv("SPACES_SECRET_ACCESS_KEY")
    spaces_endpoint = os.getenv("SPACES_ENDPOINT")
    
    if spaces_key and not os.getenv("AWS_ACCESS_KEY_ID"):
        os.environ["AWS_ACCESS_KEY_ID"] = spaces_key
    
    if spaces_secret and not os.getenv("AWS_SECRET_ACCESS_KEY"):
        os.environ["AWS_SECRET_ACCESS_KEY"] = spaces_secret
    
    # Build endpoint URL from SPACES_ENDPOINT if provided
    if spaces_endpoint and not os.getenv("AWS_S3_ENDPOINT"):
        # SPACES_ENDPOINT is just the domain (e.g., "nyc3.digitaloceanspaces.com")
        # Convert to full URL format for GDAL
        endpoint = f"https://{spaces_endpoint}".rstrip("/")
        os.environ["AWS_S3_ENDPOINT"] = endpoint
    
    # Handle AWS_S3_ENDPOINT if set directly (for backward compatibility)
    endpoint = os.getenv("AWS_S3_ENDPOINT")
    if endpoint:
        # Remove protocol if present and ensure no trailing slash, then add https://
        endpoint_clean = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
        # GDAL expects format: https://region.digitaloceanspaces.com
        os.environ["AWS_S3_ENDPOINT"] = f"https://{endpoint_clean}"
        
    # Ensure allowed extensions are set for security
    if not os.getenv("CPL_VSIL_CURL_ALLOWED_EXTENSIONS"):
        os.environ["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tif,.TIF,.tiff,.cog"


def has_s3_credentials() -> bool:
    """
    Check if S3 credentials are configured.
    
    Supports both AWS_* and SPACES_* environment variables.
    
    Returns:
        True if AWS_ACCESS_KEY_ID or SPACES_ACCESS_KEY_ID is set, False otherwise
    """
    return bool(os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("SPACES_ACCESS_KEY_ID"))


def http_to_vsi_path(url: str) -> Optional[str]:
    """
    Convert an HTTP URL to a VSI path for S3-compatible storage.
    
    This enables authenticated access when credentials are configured.
    Works with AWS S3, DigitalOcean Spaces, and other S3-compatible services.
    
    Args:
        url: HTTP/HTTPS URL to convert (e.g., https://salty-data.nyc3.digitaloceanspaces.com/bucket/path/file.tif)
    
    Returns:
        VSI path (e.g., /vsis3/bucket/path/file.tif) if conversion is possible,
        None if credentials are not configured or URL doesn't match S3 pattern
    
    Example:
        >>> http_to_vsi_path("https://salty-data.nyc3.digitaloceanspaces.com/mid_atlantic/file.tif")
        '/vsis3/salty-data/mid_atlantic/file.tif'
    """
    if not has_s3_credentials():
        return None
    
    parsed = urlparse(url)
    
    # Extract bucket name from hostname
    # Format: bucket.region.digitaloceanspaces.com or bucket.s3.region.amazonaws.com
    hostname_parts = parsed.hostname.split(".")
    
    # DigitalOcean Spaces: bucket.region.digitaloceanspaces.com
    if "digitaloceanspaces" in hostname_parts:
        bucket = hostname_parts[0]
        # Remove leading slash and construct VSI path
        path = parsed.path.lstrip("/")
        return f"/vsis3/{bucket}/{path}"
    
    # AWS S3: bucket.s3.region.amazonaws.com or bucket.s3-region.amazonaws.com
    if "s3" in hostname_parts and "amazonaws" in hostname_parts:
        bucket = hostname_parts[0]
        path = parsed.path.lstrip("/")
        return f"/vsis3/{bucket}/{path}"
    
    # S3 virtual-hosted style: bucket.s3.amazonaws.com
    if len(hostname_parts) == 3 and hostname_parts[1] == "s3" and hostname_parts[2] == "amazonaws":
        bucket = hostname_parts[0]
        path = parsed.path.lstrip("/")
        return f"/vsis3/{bucket}/{path}"
    
    return None


def get_cog_path(url: str, prefer_vsi: bool = True) -> str:
    """
    Get the best path format for a COG URL.
    
    If credentials are configured and prefer_vsi is True, returns VSI path.
    Otherwise, returns the original HTTP URL.
    
    Args:
        url: HTTP/HTTPS URL to a COG file
        prefer_vsi: If True, attempt to convert to VSI path when credentials are available
    
    Returns:
        VSI path if credentials are available and conversion is possible,
        otherwise the original HTTP URL
    """
    if prefer_vsi and has_s3_credentials():
        vsi_path = http_to_vsi_path(url)
        if vsi_path:
            # Log the conversion for debugging (only in debug mode to avoid spam)
            if os.getenv("DEBUG", "false").lower() == "true":
                print(f"[S3] Converting URL to VSI path: {url} -> {vsi_path}")
            return vsi_path
        elif url.startswith("http") and ("digitaloceanspaces" in url or "s3.amazonaws" in url):
            # Log when credentials are available but conversion failed
            if os.getenv("DEBUG", "false").lower() == "true":
                print(f"[S3] Credentials available but URL conversion failed: {url}")
    
    return url

