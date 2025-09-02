#!/bin/bash
# Emergency Rollback Script for Service Migration
# Rolls back from unified match-list-processor to previous state
# Issue #53: Migration Tooling and Scripts

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
ROLLBACK_TIMESTAMP=$(date +%Y%m%d_%H%M%S)

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

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

show_banner() {
    echo "🔄 Emergency Rollback Tool"
    echo "=========================="
    echo "Rolling back service migration"
    echo "Timestamp: $ROLLBACK_TIMESTAMP"
    echo
}

check_prerequisites() {
    log_step "Checking prerequisites..."

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

    log_success "Prerequisites check passed"
}

validate_backup_directory() {
    local backup_dir="$1"

    log_step "Validating backup directory..."

    if [[ ! -d "$backup_dir" ]]; then
        log_error "Backup directory not found: $backup_dir"
        exit 1
    fi

    # Check for required backup files
    local required_files=(
        "migration_metadata.json"
        "docker-compose.yml"
    )

    for file in "${required_files[@]}"; do
        if [[ ! -f "$backup_dir/$file" ]]; then
            log_error "Required backup file not found: $backup_dir/$file"
            exit 1
        fi
    done

    log_success "Backup directory validation passed"
}

stop_current_services() {
    log_step "Stopping current services..."

    cd "$PROJECT_DIR"

    # Stop all services
    log_info "Stopping unified processor services..."
    docker-compose down --remove-orphans || true

    # Wait for graceful shutdown
    sleep 5

    # Force stop any remaining containers
    if docker ps --format "table {{.Names}}" | grep -q "process-matches-service"; then
        log_warning "Force stopping remaining containers..."
        docker stop process-matches-service || true
        docker rm process-matches-service || true
    fi

    log_success "Current services stopped"
}

restore_configuration() {
    local backup_dir="$1"

    log_step "Restoring configuration from backup..."

    # Create rollback backup of current state
    local current_backup_dir="${PROJECT_DIR}/rollback_backup_${ROLLBACK_TIMESTAMP}"
    mkdir -p "$current_backup_dir"

    # Backup current configuration before restoring
    cp "${PROJECT_DIR}/docker-compose.yml" "$current_backup_dir/" 2>/dev/null || true
    cp "${PROJECT_DIR}/.env" "$current_backup_dir/" 2>/dev/null || true

    # Restore configuration files from backup
    if [[ -f "$backup_dir/docker-compose.yml" ]]; then
        cp "$backup_dir/docker-compose.yml" "${PROJECT_DIR}/"
        log_info "Restored docker-compose.yml"
    fi

    if [[ -f "$backup_dir/.env" ]]; then
        cp "$backup_dir/.env" "${PROJECT_DIR}/"
        log_info "Restored .env file"
    fi

    # Restore config directory if it exists
    if [[ -d "$backup_dir/config" ]]; then
        cp -r "$backup_dir/config" "${PROJECT_DIR}/"
        log_info "Restored config directory"
    fi

    log_success "Configuration restored from backup"
    log_info "Current state backed up to: $current_backup_dir"
}

restore_data() {
    local backup_dir="$1"
    local restore_data="$2"

    if [[ "$restore_data" == "true" ]]; then
        log_step "Restoring data from backup..."

        # Check if data backup exists
        if [[ -f "$backup_dir/process-matches-data.tar.gz" ]]; then
            log_info "Restoring process-matches-data volume..."

            # Create temporary container to restore data
            docker run --rm \
                -v process-matches-data:/data \
                -v "$backup_dir":/backup \
                alpine sh -c "cd /data && tar xzf /backup/process-matches-data.tar.gz" || {
                log_error "Failed to restore data volume"
                exit 1
            }

            log_success "Data volume restored"
        else
            log_warning "No data backup found - skipping data restoration"
        fi
    else
        log_info "Skipping data restoration (--restore-data not specified)"
    fi
}

validate_rollback() {
    log_step "Validating rollback..."

    # Validate configuration
    log_info "Validating restored configuration..."
    if docker-compose config --quiet; then
        log_success "Configuration validation passed"
    else
        log_error "Configuration validation failed"
        exit 1
    fi

    # Check if we can start services
    log_info "Testing service startup..."
    docker-compose up -d || {
        log_error "Failed to start services after rollback"
        exit 1
    }

    # Wait for services to start
    sleep 10

    # Check service status
    if docker-compose ps | grep -q "Up"; then
        log_success "Services started successfully"
    else
        log_error "Services failed to start properly"
        docker-compose logs
        exit 1
    fi

    log_success "Rollback validation passed"
}

show_rollback_summary() {
    local backup_dir="$1"

    log_step "Rollback Summary"
    echo
    echo "✅ Rollback completed successfully!"
    echo "📁 Backup used: $backup_dir"
    echo "📁 Current state backup: ${PROJECT_DIR}/rollback_backup_${ROLLBACK_TIMESTAMP}"
    echo "🔗 Service status: docker-compose ps"
    echo
    echo "Useful commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Check status: docker-compose ps"
    echo "  Stop services: docker-compose down"
    echo
}

main() {
    show_banner

    # Parse command line arguments
    BACKUP_DIR=""
    RESTORE_DATA=false
    FORCE_ROLLBACK=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            --restore-data)
                RESTORE_DATA=true
                shift
                ;;
            --force)
                FORCE_ROLLBACK=true
                shift
                ;;
            --help)
                echo "Usage: $0 --backup-dir BACKUP_DIR [OPTIONS]"
                echo "Options:"
                echo "  --backup-dir DIR   Directory containing migration backup"
                echo "  --restore-data     Restore data volumes from backup"
                echo "  --force           Force rollback even if validation fails"
                echo "  --help            Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$BACKUP_DIR" ]]; then
        log_error "Backup directory is required. Use --backup-dir option."
        exit 1
    fi

    # Confirm rollback
    if [[ "$FORCE_ROLLBACK" != "true" ]]; then
        echo "⚠️  WARNING: This will rollback the service migration!"
        echo "Backup directory: $BACKUP_DIR"
        echo "Restore data: $RESTORE_DATA"
        echo
        read -p "Are you sure you want to proceed? (yes/no): " -r
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            echo "Rollback cancelled."
            exit 0
        fi
    fi

    # Check if we're in the right directory
    if [[ ! -f "${PROJECT_DIR}/docker-compose.yml" ]]; then
        log_error "docker-compose.yml not found. Please run from the project root."
        exit 1
    fi

    # Run rollback steps
    check_prerequisites
    validate_backup_directory "$BACKUP_DIR"
    stop_current_services
    restore_configuration "$BACKUP_DIR"
    restore_data "$BACKUP_DIR" "$RESTORE_DATA"
    validate_rollback
    show_rollback_summary "$BACKUP_DIR"

    log_success "🎉 Rollback completed successfully!"
}

# Run main function
main "$@"
