#!/bin/bash
# Setup Redis for Salty Tiler development

echo "🚀 Setting up Redis for Salty Tiler..."

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "❌ Redis not found. Installing..."
    
    # macOS with Homebrew
    if command -v brew &> /dev/null; then
        echo "📦 Installing Redis with Homebrew..."
        brew install redis
    # Ubuntu/Debian
    elif command -v apt-get &> /dev/null; then
        echo "📦 Installing Redis with apt..."
        sudo apt-get update
        sudo apt-get install -y redis-server
    # CentOS/RHEL
    elif command -v yum &> /dev/null; then
        echo "📦 Installing Redis with yum..."
        sudo yum install -y redis
    else
        echo "❌ Unable to install Redis automatically. Please install manually."
        exit 1
    fi
else
    echo "✅ Redis is already installed"
fi

# Start Redis server
echo "🔄 Starting Redis server..."
if command -v brew &> /dev/null && brew services list | grep redis | grep started > /dev/null; then
    echo "✅ Redis is already running (Homebrew)"
elif pgrep redis-server > /dev/null; then
    echo "✅ Redis is already running"
else
    # Try to start Redis
    if command -v brew &> /dev/null; then
        brew services start redis
        echo "✅ Started Redis with Homebrew"
    else
        # Start Redis in background
        redis-server --daemonize yes
        echo "✅ Started Redis daemon"
    fi
fi

# Test Redis connection
echo "🧪 Testing Redis connection..."
if redis-cli ping | grep PONG > /dev/null; then
    echo "✅ Redis is responding to ping"
else
    echo "❌ Redis is not responding"
    exit 1
fi

# Show Redis info
echo "📊 Redis server info:"
redis-cli info server | grep "redis_version\|os\|process_id"

echo ""
echo "🎉 Redis setup complete!"
echo ""
echo "To enable Redis caching in Salty Tiler:"
echo "1. Copy env.example to .env"
echo "2. Set CACHE_TYPE=redis in .env"
echo "3. Restart your Salty Tiler server"
echo ""
echo "To test caching:"
echo "python test_redis_cache.py"
