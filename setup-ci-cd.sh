#!/bin/bash

echo "🌊 Salty Tiler - CI/CD Setup Script"
echo "This script will help you configure GitHub secrets for automated deployment"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI (gh) is not installed."
    echo "Please install it from: https://cli.github.com/"
    echo "Or run: brew install gh"
    exit 1
fi

# Check if user is logged in to GitHub CLI
if ! gh auth status &> /dev/null; then
    print_error "You are not logged in to GitHub CLI."
    echo "Please run: gh auth login"
    exit 1
fi

print_step "Setting up GitHub secrets for automated deployment..."
echo ""

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
print_success "Repository: $REPO"
echo ""

# Prompt for deployment server details
print_step "Enter your deployment server details:"
echo ""

read -p "🖥️  Server hostname or IP: " DEPLOY_HOST
read -p "👤 SSH username: " DEPLOY_USER
read -p "🔑 Path to SSH private key (default: ~/.ssh/id_rsa): " SSH_KEY_PATH

# Default SSH key path
if [ -z "$SSH_KEY_PATH" ]; then
    SSH_KEY_PATH="$HOME/.ssh/id_rsa"
fi

# Validate SSH key exists
if [ ! -f "$SSH_KEY_PATH" ]; then
    print_error "SSH key not found at: $SSH_KEY_PATH"
    echo "Please create an SSH key pair or specify the correct path."
    exit 1
fi

# Test SSH connection
print_step "Testing SSH connection..."
if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
    print_success "SSH connection test passed"
else
    print_warning "SSH connection test failed. Please ensure:"
    echo "  - Server is accessible"
    echo "  - SSH key is added to server's authorized_keys"
    echo "  - Username and hostname are correct"
    echo ""
    read -p "Continue anyway? (y/N): " CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set GitHub secrets
print_step "Setting GitHub repository secrets..."
echo ""

# Set DEPLOY_HOST
echo "Setting DEPLOY_HOST..."
echo "$DEPLOY_HOST" | gh secret set DEPLOY_HOST
print_success "DEPLOY_HOST set"

# Set DEPLOY_USER  
echo "Setting DEPLOY_USER..."
echo "$DEPLOY_USER" | gh secret set DEPLOY_USER
print_success "DEPLOY_USER set"

# Set DEPLOY_SSH_KEY
echo "Setting DEPLOY_SSH_KEY..."
gh secret set DEPLOY_SSH_KEY < "$SSH_KEY_PATH"
print_success "DEPLOY_SSH_KEY set"

echo ""
print_success "GitHub secrets configured successfully!"
echo ""

print_step "Next steps:"
echo "1. Ensure your server has Docker and Docker Compose installed"
echo "2. Clone your repository to /salty-tiler on the server:"
echo "   git clone https://github.com/$REPO.git /salty-tiler"
echo "3. Set up the salty_network on your server:"
echo "   docker network create salty_network"
echo "4. Push to main branch to trigger deployment"
echo ""

print_step "Server setup commands:"
echo "Run these commands on your deployment server:"
echo ""
echo "# Install Docker (if not already installed)"
echo "curl -fsSL https://get.docker.com -o get-docker.sh"
echo "sudo sh get-docker.sh"
echo "sudo usermod -aG docker $DEPLOY_USER"
echo ""
echo "# Install Docker Compose (if not already installed)"
echo "sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose"
echo "sudo chmod +x /usr/local/bin/docker-compose"
echo ""
echo "# Clone repository"
echo "sudo git clone https://github.com/$REPO.git /salty-tiler"
echo "sudo chown -R $DEPLOY_USER:$DEPLOY_USER /salty-tiler"
echo ""
echo "# Create Docker network"
echo "docker network create salty_network"
echo ""
echo "# Test deployment"
echo "cd /salty-tiler && ./deploy.sh"
echo ""

print_success "Setup complete! 🎉"
echo "Push to main branch to trigger your first automated deployment." 