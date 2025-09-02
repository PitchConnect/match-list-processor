#!/bin/bash
# Migration Script for Service Consolidation
# Migrates from match-list-change-detector to unified match-list-processor
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
MIGRATION_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${PROJECT_DIR}/migration_backup_${MIGRATION_TIMESTAMP}"

# Migration configuration
OLD_SERVICE_NAME="match-list-change-detector"
NEW_SERVICE_NAME="process-matches-service"
OLD_COMPOSE_FILE="docker-compose.yml"
NEW_COMPOSE_FILE="docker-compose.yml"

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
    echo "🔄 Service Migration Tool"
    echo "========================="
    echo "From: match-list-change-detector"
    echo "To:   unified match-list-processor"
    echo "Timestamp: $MIGRATION_TIMESTAMP"
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

    # Check Python (for migration utilities)
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required for migration utilities"
        exit 1
    fi

    # Check if we're in the right directory
    if [[ ! -f "${PROJECT_DIR}/docker-compose.yml" ]]; then
        log_error "docker-compose.yml not found. Please run from the project root."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

validate_pre_migration() {
    log_step "Validating pre-migration state..."

    # Check if old service is running
    if docker ps --format "table {{.Names}}" | grep -q "$OLD_SERVICE_NAME"; then
        log_info "Found running old service: $OLD_SERVICE_NAME"
        OLD_SERVICE_RUNNING=true
    else
        log_warning "Old service $OLD_SERVICE_NAME not found running"
        OLD_SERVICE_RUNNING=false
    fi

    # Check data volumes
    log_info "Checking data volumes..."
    if docker volume ls | grep -q "process-matches-data"; then
        log_info "Found process-matches-data volume"
    else
        log_warning "process-matches-data volume not found"
    fi

    # Check network connectivity
    log_info "Testing network connectivity..."
    if docker network ls | grep -q "fogis-network"; then
        log_info "Found fogis-network"
    else
        log_warning "fogis-network not found - will be created"
    fi

    # Validate configuration files
    log_info "Validating configuration..."
    if [[ -f "${PROJECT_DIR}/docker-compose.yml" ]]; then
        if docker-compose -f "${PROJECT_DIR}/docker-compose.yml" config --quiet; then
            log_success "Docker Compose configuration is valid"
        else
            log_error "Docker Compose configuration validation failed"
            exit 1
        fi
    else
        log_error "docker-compose.yml not found"
        exit 1
    fi

    log_success "Pre-migration validation complete"
}

backup_current_state() {
    log_step "Creating backup of current state..."

    mkdir -p "$BACKUP_DIR"

    # Backup configuration files
    log_info "Backing up configuration files..."
    cp "${PROJECT_DIR}/docker-compose.yml" "$BACKUP_DIR/" 2>/dev/null || true
    cp "${PROJECT_DIR}/.env" "$BACKUP_DIR/" 2>/dev/null || true
    cp -r "${PROJECT_DIR}/config" "$BACKUP_DIR/" 2>/dev/null || true

    # Backup data volumes
    log_info "Backing up data volumes..."
    if docker volume ls | grep -q "process-matches-data"; then
        log_info "Backing up process-matches-data volume..."
        docker run --rm \
            -v process-matches-data:/data \
            -v "$BACKUP_DIR":/backup \
            alpine tar czf /backup/process-matches-data.tar.gz -C /data . 2>/dev/null || true
    fi

    # Create migration metadata
    cat > "$BACKUP_DIR/migration_metadata.json" << EOF
{
    "migration_timestamp": "$MIGRATION_TIMESTAMP",
    "migration_tool_version": "1.0",
    "old_service": "$OLD_SERVICE_NAME",
    "new_service": "$NEW_SERVICE_NAME",
    "backup_contents": {
        "docker_compose": $([ -f "$BACKUP_DIR/docker-compose.yml" ] && echo "true" || echo "false"),
        "env_file": $([ -f "$BACKUP_DIR/.env" ] && echo "true" || echo "false"),
        "config_dir": $([ -d "$BACKUP_DIR/config" ] && echo "true" || echo "false"),
        "data_volume": $([ -f "$BACKUP_DIR/process-matches-data.tar.gz" ] && echo "true" || echo "false")
    }
}
EOF

    log_success "Backup created in $BACKUP_DIR"
}

migrate_configuration() {
    log_step "Migrating configuration..."

    # Run Python configuration migration utility
    log_info "Running configuration migration utility..."
    python3 "${SCRIPT_DIR}/migrate_config.py" \
        --input "${PROJECT_DIR}/.env" \
        --output "${PROJECT_DIR}/.env.migrated" \
        --backup-dir "$BACKUP_DIR"

    # Validate migrated configuration
    if [[ -f "${PROJECT_DIR}/.env.migrated" ]]; then
        log_info "Validating migrated configuration..."
        python3 "${SCRIPT_DIR}/validate_migrated_config.py" \
            --config "${PROJECT_DIR}/.env.migrated"

        if [[ $? -eq 0 ]]; then
            mv "${PROJECT_DIR}/.env.migrated" "${PROJECT_DIR}/.env"
            log_success "Configuration migration complete"
        else
            log_error "Configuration migration validation failed"
            exit 1
        fi
    else
        log_error "Configuration migration failed - output file not created"
        exit 1
    fi
}

stop_old_services() {
    log_step "Stopping old services..."

    if [[ "$OLD_SERVICE_RUNNING" == "true" ]]; then
        log_info "Stopping old service gracefully..."

        # Try to stop gracefully first
        docker-compose down --remove-orphans || true

        # Wait for graceful shutdown
        sleep 10

        # Force stop if still running
        if docker ps --format "table {{.Names}}" | grep -q "$OLD_SERVICE_NAME"; then
            log_warning "Force stopping old service..."
            docker stop "$OLD_SERVICE_NAME" || true
            docker rm "$OLD_SERVICE_NAME" || true
        fi

        log_success "Old services stopped"
    else
        log_info "No old services to stop"
    fi
}

start_new_services() {
    log_step "Starting new unified service..."

    cd "$PROJECT_DIR"

    # Create networks and volumes if needed
    log_info "Creating networks and volumes..."
    "${PROJECT_DIR}/scripts/deploy.sh" --skip-backup --skip-validation

    log_success "New unified service started"
}

validate_post_migration() {
    log_step "Validating post-migration state..."

    # Wait for service to be ready
    log_info "Waiting for service to be ready..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health/simple > /dev/null 2>&1; then
            log_success "Service is ready"
            break
        fi
        echo "Waiting... ($i/30)"
        sleep 2
    done

    # Run post-migration validation
    python3 "${SCRIPT_DIR}/validate_post_migration.py" \
        --backup-dir "$BACKUP_DIR"

    log_success "Post-migration validation complete"
}

show_migration_summary() {
    log_step "Migration Summary"
    echo
    echo "✅ Migration completed successfully!"
    echo "📁 Backup location: $BACKUP_DIR"
    echo "🔗 Service URL: http://localhost:8000"
    echo "🏥 Health check: http://localhost:8000/health/simple"
    echo
    echo "Useful commands:"
    echo "  View logs: docker-compose logs -f $NEW_SERVICE_NAME"
    echo "  Check status: docker-compose ps"
    echo "  Rollback: ${SCRIPT_DIR}/rollback_migration.sh --backup-dir $BACKUP_DIR"
    echo
}

main() {
    show_banner

    # Parse command line arguments
    SKIP_BACKUP=false
    FORCE_MIGRATION=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --force)
                FORCE_MIGRATION=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --skip-backup  Skip backup creation"
                echo "  --force        Force migration even if validation fails"
                echo "  --help         Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Run migration steps
    check_prerequisites
    validate_pre_migration

    if [[ "$SKIP_BACKUP" != "true" ]]; then
        backup_current_state
    fi

    migrate_configuration
    stop_old_services
    start_new_services
    validate_post_migration
    show_migration_summary
}

# Run main function
main "$@"
