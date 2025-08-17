#!/bin/bash
set -e

echo "🌊 Salty Tiler - Docker Deployment Script"

# Configuration
IMAGE_NAME="salty-tiler"
CONTAINER_NAME="salty-tiler"
PORT="8001"

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to deploy using docker-compose
deploy_with_compose() {
    echo "🏗️  Building and deploying with docker-compose..."
    
    # Stop and remove existing containers
    echo "🛑 Stopping and removing existing containers..."
    docker-compose down --remove-orphans
    
    # Force remove the container if it still exists
    echo "🧹 Force removing any lingering container..."
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    
    # Build and start new container
    echo "🚀 Building and starting new container..."
    docker-compose up --build -d
    
    echo "✅ Container started successfully"
    echo "🌐 Service available at: http://localhost:$PORT"
    echo "📚 API documentation: http://localhost:$PORT/docs"
    echo "❤️  Health check: http://localhost:$PORT/health"
}

# Function to show logs
show_logs() {
    echo "📜 Container logs:"
    docker-compose logs -f salty-tiler
}

# Function to show status
show_status() {
    echo "📊 Container status:"
    docker-compose ps
    echo ""
    echo "🔍 Health check:"
    curl -f http://localhost:$PORT/health 2>/dev/null && echo "✅ Healthy" || echo "❌ Unhealthy"
}

# Main script logic
case "${1:-deploy}" in
    "deploy")
        check_docker
        deploy_with_compose
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
        echo "🛑 Stopping containers..."
        docker-compose down --remove-orphans
        echo "✅ Containers stopped"
        ;;
    "restart")
        echo "🔄 Restarting containers..."
        deploy_with_compose
        echo "✅ Containers restarted"
        ;;
    *)
        echo "Usage: $0 {deploy|logs|status|stop|restart}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Build and deploy container (default)"
        echo "  logs    - Show container logs"
        echo "  status  - Show container status and health"
        echo "  stop    - Stop containers"
        echo "  restart - Restart containers"
        exit 1
        ;;
esac 