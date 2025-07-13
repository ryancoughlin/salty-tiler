#!/bin/bash
set -e

echo "🌊 Salty Tiler - Docker Deployment Script"

# Configuration
IMAGE_NAME="salty-tiler"
CONTAINER_NAME="salty-tiler"
PORT="8001"
ENV_FILE="env.example"

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to build the Docker image
build_image() {
    echo "🏗️  Building Docker image: $IMAGE_NAME"
    docker build -t $IMAGE_NAME .
    echo "✅ Docker image built successfully"
}

# Function to stop and remove existing container
cleanup_container() {
    if docker ps -a --format 'table {{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
        echo "🧹 Stopping and removing existing container: $CONTAINER_NAME"
        docker stop $CONTAINER_NAME || true
        docker rm $CONTAINER_NAME || true
    fi
}

# Function to run the container
run_container() {
    echo "🚀 Starting container: $CONTAINER_NAME"
    
    # Check if env file exists
    if [ -f "$ENV_FILE" ]; then
        echo "📋 Using environment file: $ENV_FILE"
        ENV_FLAG="--env-file $ENV_FILE"
    else
        echo "⚠️  No environment file found. Using default configuration."
        ENV_FLAG=""
    fi
    
    # Run the container
    docker run -d \
        --name $CONTAINER_NAME \
        -p $PORT:8001 \
        -v "$(pwd)/sst_colormap.json:/app/sst_colormap.json:ro" \
        $ENV_FLAG \
        --restart unless-stopped \
        $IMAGE_NAME
    
    echo "✅ Container started successfully"
    echo "🌐 Service available at: http://localhost:$PORT"
    echo "📚 API documentation: http://localhost:$PORT/docs"
    echo "❤️  Health check: http://localhost:$PORT/health"
}

# Function to show logs
show_logs() {
    echo "📜 Container logs:"
    docker logs -f $CONTAINER_NAME
}

# Function to show status
show_status() {
    echo "📊 Container status:"
    docker ps --filter "name=$CONTAINER_NAME"
    echo ""
    echo "🔍 Health check:"
    curl -f http://localhost:$PORT/health 2>/dev/null && echo "✅ Healthy" || echo "❌ Unhealthy"
}

# Main script logic
case "${1:-deploy}" in
    "build")
        check_docker
        build_image
        ;;
    "deploy")
        check_docker
        build_image
        cleanup_container
        run_container
        echo ""
        echo "🎉 Deployment complete!"
        echo "   Use './deploy.sh logs' to view logs"
        echo "   Use './deploy.sh status' to check status"
        echo "   Use './deploy.sh stop' to stop the service"
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "stop")
        cleanup_container
        echo "🛑 Container stopped and removed"
        ;;
    "restart")
        cleanup_container
        run_container
        echo "🔄 Container restarted"
        ;;
    *)
        echo "Usage: $0 {build|deploy|logs|status|stop|restart}"
        echo ""
        echo "Commands:"
        echo "  build   - Build Docker image only"
        echo "  deploy  - Build and deploy container (default)"
        echo "  logs    - Show container logs"
        echo "  status  - Show container status and health"
        echo "  stop    - Stop and remove container"
        echo "  restart - Restart container"
        exit 1
        ;;
esac 