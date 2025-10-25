FROM osgeo/gdal:ubuntu-small-3.6.3

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

# Essential GDAL optimizations for TiTiler performance
ENV GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR
ENV GDAL_CACHEMAX=1024
ENV CPL_VSIL_CURL_CACHE_SIZE=1000000000
ENV VSI_CACHE=TRUE
ENV VSI_CACHE_SIZE=200000000
ENV GDAL_HTTP_MERGE_CONSECUTIVE_RANGES=YES
ENV GDAL_HTTP_MULTIPLEX=YES
ENV GDAL_HTTP_VERSION=2
ENV GDAL_BAND_BLOCK_CACHE=HASHSET

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
CMD ["gunicorn", "app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8001", "--timeout", "120", "--graceful-timeout", "30", "--keep-alive", "5", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]