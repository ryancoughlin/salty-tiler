FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.3

# Install Python 3 and pip (using system default Python version)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for python and pip
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Set environment variables for GDAL
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV GDAL_DATA=/usr/share/gdal

# Configure GDAL for better HTTP handling - increase timeouts for production
ENV GDAL_HTTP_VERSION=2
ENV GDAL_HTTP_USERAGENT="SaltyTiler/1.0"
ENV GDAL_HTTP_MAX_RETRY=5
ENV GDAL_HTTP_RETRY_DELAY=2
ENV GDAL_HTTP_TIMEOUT=60
ENV GDAL_HTTP_PROXY=""
ENV GDAL_HTTP_PROXYUSERPWD=""
ENV GDAL_HTTP_UNSAFESSL=1

# Enable connection pooling and concurrent access with higher limits
ENV GDAL_HTTP_MAX_CONCURRENT=20
ENV GDAL_HTTP_CONNECTION_TIMEOUT=30
ENV GDAL_HTTP_READ_TIMEOUT=60

# Optimize GDAL for COG performance and HTTP range requests
ENV GDAL_HTTP_MERGE_CONSECUTIVE_RANGES=YES
ENV GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR
ENV CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.tiff"
ENV VSI_CACHE=TRUE
ENV VSI_CACHE_SIZE=50000000
ENV GDAL_CACHEMAX=200
ENV CPL_VSIL_CURL_CACHE_SIZE=200000000
ENV GDAL_HTTP_MULTIPLEX=YES

# Keep range requests enabled for now
ENV GDAL_HTTP_USE_RANGE=1
ENV GDAL_HTTP_USE_HEAD=1
ENV GDAL_HTTP_USE_MULTIPART=1
ENV GDAL_HTTP_VERIFYSSL=0
ENV GDAL_HTTP_HEADERS=""

# Enable GDAL drivers for HTTP
ENV GDAL_DRIVER_PATH=/usr/lib/gdal/3.11
ENV GDAL_SKIP=""

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install Python dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8001

# Ensure virtual environment is active for runtime
ENV PATH="/opt/venv/bin:$PATH"

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"] 