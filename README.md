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

## License

This project is part of the PitchConnect ecosystem. Please refer to the organization's licensing terms.

## Support

For questions or issues:

1. Check existing [GitHub Issues](https://github.com/PitchConnect/match-list-processor/issues)
2. Create a new issue with detailed information
3. Follow the guidelines in [CONTRIBUTING.md](CONTRIBUTING.md)
