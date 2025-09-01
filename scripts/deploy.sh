#!/bin/bash
# Deployment script for unified match processor service
# Updated: 2025-09-01 - Issue #25 implementation

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_DIR}/.env"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"
CONFIG_FILE="${PROJECT_DIR}/config/unified_processor.yml"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi

    # Check Python (for validation)
    if ! command -v python3 &> /dev/null; then
        log_warning "Python 3 is not available - skipping configuration validation"
        SKIP_VALIDATION=true
    fi

    log_success "Prerequisites check passed"
}

validate_configuration() {
    if [[ "${SKIP_VALIDATION:-false}" == "true" ]]; then
        log_warning "Skipping configuration validation (Python not available)"
        return 0
    fi

    log_info "Validating configuration..."

    cd "$PROJECT_DIR"

    # Install required Python packages for validation
    if [[ -f "requirements.txt" ]]; then
        python3 -m pip install -q pyyaml
    fi

    # Run configuration validation
    if python3 scripts/validate_config.py --env-file "$ENV_FILE" 2>/dev/null; then
        log_success "Configuration validation passed"
    else
        log_error "Configuration validation failed"
        log_info "Run 'python3 scripts/validate_config.py' for detailed error information"
        exit 1
    fi
}

backup_data() {
    log_info "Creating data backup..."

    BACKUP_DIR="${PROJECT_DIR}/backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    # Backup configuration files
    cp "$COMPOSE_FILE" "$BACKUP_DIR/" 2>/dev/null || true
    cp "$ENV_FILE" "$BACKUP_DIR/" 2>/dev/null || true

    # Backup Docker volumes if they exist
    if docker volume ls | grep -q "process-matches-data"; then
        log_info "Backing up process-matches-data volume..."
        docker run --rm \
            -v process-matches-data:/data \
            -v "$BACKUP_DIR":/backup \
            alpine tar czf /backup/process-matches-data.tar.gz -C /data . 2>/dev/null || true
    fi

    log_success "Backup created in $BACKUP_DIR"
}

create_networks_and_volumes() {
    log_info "Creating Docker networks and volumes..."

    # Create external network if it doesn't exist
    if ! docker network ls | grep -q "fogis-network"; then
        docker network create fogis-network
        log_success "Created fogis-network"
    else
        log_info "fogis-network already exists"
    fi

    # Create external volumes if they don't exist
    if ! docker volume ls | grep -q "process-matches-data"; then
        docker volume create process-matches-data
        log_success "Created process-matches-data volume"
    else
        log_info "process-matches-data volume already exists"
    fi

    if ! docker volume ls | grep -q "google-drive-service-data"; then
        docker volume create google-drive-service-data
        log_success "Created google-drive-service-data volume"
    else
        log_info "google-drive-service-data volume already exists"
    fi
}

deploy_services() {
    log_info "Deploying services..."

    cd "$PROJECT_DIR"

    # Pull latest images
    log_info "Pulling latest images..."
    docker-compose pull

    # Stop existing services
    log_info "Stopping existing services..."
    docker-compose down

    # Start services
    log_info "Starting services..."
    docker-compose up -d

    log_success "Services deployed successfully"
}

verify_deployment() {
    log_info "Verifying deployment..."

    # Wait for services to start
    sleep 10

    # Check service status
    log_info "Checking service status..."
    docker-compose ps

    # Check main service health
    log_info "Checking main service health..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health/simple &>/dev/null; then
            log_success "Main service health check passed"
            break
        elif [[ $i -eq 30 ]]; then
            log_error "Main service health check failed after 30 attempts"
            log_info "Service logs:"
            docker-compose logs process-matches-service | tail -20
            exit 1
        else
            log_info "Waiting for service to be ready... (attempt $i/30)"
            sleep 2
        fi
    done

    # Check logs for errors
    log_info "Checking for errors in logs..."
    if docker-compose logs process-matches-service | grep -i error | grep -v "test\|debug"; then
        log_warning "Found errors in service logs - please review"
    else
        log_success "No errors found in service logs"
    fi
}

show_status() {
    log_info "Deployment Status:"
    echo
    echo "Services:"
    docker-compose ps
    echo
    echo "Health Check:"
    curl -s http://localhost:8000/health/simple | python3 -m json.tool 2>/dev/null || echo "Health check endpoint not responding"
    echo
    echo "Useful Commands:"
    echo "  View logs: docker-compose logs -f process-matches-service"
    echo "  Check status: docker-compose ps"
    echo "  Stop services: docker-compose down"
    echo "  Restart services: docker-compose restart"
    echo
}

main() {
    echo "🚀 Unified Match Processor Deployment Script"
    echo "============================================="
    echo

    # Parse command line arguments
    SKIP_BACKUP=false
    SKIP_VALIDATION=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --skip-validation)
                SKIP_VALIDATION=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --skip-backup      Skip data backup"
                echo "  --skip-validation  Skip configuration validation"
                echo "  --help            Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Check if we're in the right directory
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "docker-compose.yml not found. Please run this script from the project root."
        exit 1
    fi

    # Run deployment steps
    check_prerequisites

    if [[ "$SKIP_VALIDATION" != "true" ]]; then
        validate_configuration
    fi

    if [[ "$SKIP_BACKUP" != "true" ]]; then
        backup_data
    fi

    create_networks_and_volumes
    deploy_services
    verify_deployment
    show_status

    log_success "🎉 Deployment completed successfully!"
    echo
    log_info "The unified match processor service is now running."
    log_info "Access the health check at: http://localhost:8000/health/simple"
}

# Run main function
main "$@"
