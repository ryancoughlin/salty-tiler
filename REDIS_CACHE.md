# Redis Caching for Salty Tiler

This document explains how to set up and use Redis-backed caching for optimal tile serving performance.

## Overview

Salty Tiler supports two caching backends:
- **In-memory caching** (default) - Fast but limited by server memory
- **Redis caching** - Persistent, scalable, and shared across server instances

## Quick Setup

### 1. Install Redis

```bash
# Run the setup script
./setup_redis.sh

# Or install manually:
# macOS
brew install redis && brew services start redis

# Ubuntu/Debian  
sudo apt-get install redis-server

# CentOS/RHEL
sudo yum install redis
```

### 2. Configure Caching

```bash
# Copy environment template
cp env.example .env

# Edit .env and set:
CACHE_TYPE=redis
CACHE_REDIS_HOST=localhost
CACHE_REDIS_PORT=6379
CACHE_REDIS_DB=0
CACHE_TTL=86400
```

### 3. Install Dependencies

```bash
# Install Redis Python client
pip install -r requirements.txt
```

### 4. Test Caching

```bash
# Start the server
python app.py

# In another terminal, test caching
python test_redis_cache.py
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TYPE` | `memory` | Cache backend: `memory` or `redis` |
| `CACHE_TTL` | `86400` | Cache TTL in seconds (24 hours) |
| `CACHE_NAMESPACE` | `salty-tiler` | Redis key namespace |
| `CACHE_REDIS_HOST` | `localhost` | Redis server hostname |
| `CACHE_REDIS_PORT` | `6379` | Redis server port |
| `CACHE_REDIS_DB` | `0` | Redis database number |
| `CACHE_REDIS_PASSWORD` | | Redis password (if required) |

### Cache Key Format

Cache keys are optimized for Redis storage:

```
tile:{url_hash}:{z}:{x}:{y}:{rescale_hash}:{colormap}:{expr_hash}
```

Example:
```
tile:a1b2c3d4:4:4:6:f5e6d7:sst_high_contrast:default
```

This format ensures:
- **Uniqueness**: Different parameters generate different keys
- **Compactness**: Hashed components keep keys short
- **Readability**: Tile coordinates and colormap are human-readable

## Performance Benefits

### Cache Hit Performance

| Scenario | Memory Cache | Redis Cache | No Cache |
|----------|--------------|-------------|-----------|
| Local COG | ~5ms | ~15ms | ~200ms |
| Remote COG | ~5ms | ~15ms | ~2000ms |
| Complex Expression | ~5ms | ~15ms | ~500ms |

### Memory Usage

- **Memory Cache**: Limited by server RAM, lost on restart
- **Redis Cache**: Persistent, configurable memory limits, shared across instances

## Monitoring

### Cache Headers

Every tile response includes debugging headers:

```http
X-Cache: HIT|MISS
X-Cache-Key: tile:a1b2c3d4:4:4:6:f5e6d7:sst_high_contrast:default
X-Tile-Coords: 4/4/6
```

### Redis Monitoring

```bash
# Monitor Redis activity
redis-cli monitor

# Check cache statistics
redis-cli info stats

# List cached tiles
redis-cli keys "salty-tiler:tile:*"

# Check memory usage
redis-cli info memory
```

### Server Logs

Cache operations are logged with performance metrics:

```
[CACHE] Initialized Redis at localhost:6379/0 cache with TTL=86400s, namespace='salty-tiler'
[CACHE] MISS: URL cogs/sst.tif z=4 x=4 y=6 min=71.4 max=81.6 scale=LINEAR expr=b1
[CACHE] HIT: URL cogs/sst.tif z=4 x=4 y=6 min=71.4 max=81.6 scale=LINEAR expr=b1
```

## Production Deployment

### Redis Configuration

For production, configure Redis with:

```redis
# /etc/redis/redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Docker Compose

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru

  salty-tiler:
    build: .
    environment:
      - CACHE_TYPE=redis
      - CACHE_REDIS_HOST=redis
    depends_on:
      - redis

volumes:
  redis_data:
```

### Environment Variables

```bash
# Production settings
CACHE_TYPE=redis
CACHE_TTL=86400
CACHE_REDIS_HOST=redis-cluster.example.com
CACHE_REDIS_PORT=6379
CACHE_REDIS_PASSWORD=your-secure-password
CACHE_NAMESPACE=salty-tiler-prod
```

## Troubleshooting

### Common Issues

**Redis Connection Failed**
```bash
# Check Redis is running
redis-cli ping

# Check network connectivity
telnet localhost 6379
```

**Cache Not Working**
```bash
# Check cache configuration
curl -I http://localhost:8001/cog/tiles/WebMercatorQuad/4/4/6.png?url=...
# Look for X-Cache header

# Monitor Redis activity
redis-cli monitor
```

**High Memory Usage**
```bash
# Check Redis memory
redis-cli info memory

# Clear cache if needed
redis-cli flushdb
```

### Performance Tuning

1. **Adjust TTL**: Longer TTL = better hit rate, more memory usage
2. **Monitor hit rate**: Aim for >80% hit rate in production
3. **Scale Redis**: Use Redis Cluster for high-traffic deployments
4. **Optimize keys**: Current key format is already optimized

## Development

### Testing Changes

```bash
# Test with memory cache
CACHE_TYPE=memory python app.py

# Test with Redis cache  
CACHE_TYPE=redis python app.py

# Run cache performance tests
python test_redis_cache.py
```

### Cache Invalidation

Currently, cache entries expire based on TTL. For manual invalidation:

```bash
# Clear specific tile
redis-cli del "salty-tiler:tile:a1b2c3d4:4:4:6:f5e6d7:sst_high_contrast:default"

# Clear all tiles for a COG
redis-cli keys "salty-tiler:tile:a1b2c3d4:*" | xargs redis-cli del

# Clear entire cache
redis-cli flushdb
```

## Next Steps

- [ ] Add cache warming for popular tiles
- [ ] Implement cache invalidation API
- [ ] Add Prometheus metrics for cache performance
- [ ] Support Redis Cluster for horizontal scaling
