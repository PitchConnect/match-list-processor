# Match List Processor

A microservice that processes football match lists, detects changes, and generates WhatsApp group assets for referee teams.

## Overview

The Match List Processor is part of the fogis-network ecosystem and handles:

- Fetching match lists from the FOGIS API
- Detecting changes in match assignments
- Generating WhatsApp group descriptions and avatars
- Uploading assets to Google Drive
- Syncing referee contact information

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for development)
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/PitchConnect/match-list-processor.git
cd match-list-processor

# Set up development environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks (recommended)
pip install pre-commit
pre-commit install

# Run tests
python -m pytest

# Run linting and formatting
python -m flake8 src/ tests/
python -m black src/ tests/
python -m mypy src/
```

### Docker Setup

```bash
# Create required Docker volumes
docker volume create process-matches-data
docker volume create google-drive-service-data

# Create Docker network (if not already created)
docker network create fogis-network

# Run the service
./run.sh
```

## Development Workflow

### Code Quality Tools

This project uses several tools to maintain code quality:

- **Black**: Code formatting
- **flake8**: Linting and style checking
- **isort**: Import sorting
- **mypy**: Type checking
- **bandit**: Security scanning
- **pytest**: Testing framework

### Pre-commit Hooks

Pre-commit hooks automatically run quality checks before each commit:

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files

# Run specific hooks
pre-commit run black      # Format code
pre-commit run flake8     # Lint code
pre-commit run mypy       # Type check
pre-commit run bandit     # Security scan
```

The hooks will automatically fix formatting issues and prevent commits that don't meet quality standards.

### Testing

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/test_app.py

# Run tests with verbose output
python -m pytest -v
```

### Type Checking

```bash
# Check types in source code
python -m mypy src/

# Check specific file
python -m mypy src/app.py
```

## Architecture

The service follows a modular architecture with clear separation of concerns:

- **Core**: Business logic (match processing, comparison, data management)
- **Services**: External service integrations (API clients, storage, avatars)
- **Utils**: Utility functions (file operations, description generation)
- **Interfaces**: Abstract base classes for dependency injection

## Configuration

Configuration is managed through environment variables and Pydantic settings:

```bash
# Required environment variables
FOGIS_API_CLIENT_URL=http://fogis-api-client-service:8080
WHATSAPP_AVATAR_SERVICE_URL=http://whatsapp-avatar-service:5002
GOOGLE_DRIVE_SERVICE_URL=http://google-drive-service:5000
PHONEBOOK_SYNC_SERVICE_URL=http://fogis-calendar-phonebook-sync:5003

# Optional configuration
DATA_FOLDER=/data
MIN_REFEREES_FOR_WHATSAPP=2
LOG_LEVEL=INFO
```

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:

- Development workflow
- Code standards
- Testing requirements
- Pull request process
- Pre-commit hook setup

## CI/CD Pipeline

The project includes a comprehensive CI/CD pipeline that runs:

- **Code formatting** (Black, isort)
- **Linting** (flake8)
- **Type checking** (mypy)
- **Security scanning** (bandit)
- **Unit tests** (pytest with 96% coverage requirement)
- **Docker build verification**

All checks must pass before code can be merged.

## Health Check Endpoints

The service includes comprehensive health check endpoints for monitoring and orchestration:

- **Simple Health Check**: `GET /health/simple` - Lightweight check without dependencies
- **Comprehensive Health**: `GET /health` - Full health status including dependency checks
- **Dependencies Only**: `GET /health/dependencies` - Status of all service dependencies
- **Service Info**: `GET /` - Basic service information and available endpoints

### Health Check Features

- **Docker Integration**: Built-in `HEALTHCHECK` directive with curl-based monitoring
- **Dependency Monitoring**: Checks connectivity to all required services:
  - fogis-api-client-service
  - whatsapp-avatar-service
  - google-drive-service
  - phonebook-sync-service
- **Status Levels**: `healthy`, `degraded`, `unhealthy` based on dependency availability
- **Response Time Tracking**: Monitors dependency response times
- **Graceful Degradation**: Service remains operational even with some dependency failures

### Quick Health Check

```bash
# Check if service is running
curl http://localhost:8000/health/simple

# Get comprehensive status
curl http://localhost:8000/health
```

For detailed health check documentation, see [docs/HEALTH_CHECK.md](docs/HEALTH_CHECK.md).

## Container Images

### Official Releases

Official container images are automatically built and published to GitHub Container Registry (GHCR) when version tags are created:

```bash
# Pull the latest release
docker pull ghcr.io/pitchconnect/match-list-processor:latest

# Pull a specific version
docker pull ghcr.io/pitchconnect/match-list-processor:v1.0.0

# Pull a specific major version
docker pull ghcr.io/pitchconnect/match-list-processor:1
```

### Available Tags

- `latest` - Latest stable release
- `vX.Y.Z` - Specific version (e.g., `v1.0.0`)
- `X.Y` - Major.minor version (e.g., `1.0`)
- `X` - Major version (e.g., `1`)

### Multi-Architecture Support

Images are built for multiple architectures:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64/AArch64)

### Image Verification

Container images are signed and can be verified using cosign:

```bash
cosign verify --certificate-identity-regexp="https://github.com/PitchConnect/match-list-processor" \
  --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
  ghcr.io/pitchconnect/match-list-processor:latest
```

### Creating Releases

To create a new release:

1. Create and push a version tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. The release workflow will automatically:
   - Build multi-architecture container images
   - Push images to GHCR with appropriate tags
   - Generate build attestations
   - Create a GitHub release with release notes

## License

This project is part of the PitchConnect ecosystem. Please refer to the organization's licensing terms.

## Support

For questions or issues:

1. Check existing [GitHub Issues](https://github.com/PitchConnect/match-list-processor/issues)
2. Create a new issue with detailed information
3. Follow the guidelines in [CONTRIBUTING.md](CONTRIBUTING.md)
