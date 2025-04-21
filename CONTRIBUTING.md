# Contributing to Match List Processor

Thank you for considering contributing to Match List Processor! This document provides essential guidelines for contributing to this project. For more detailed information, please refer to our [comprehensive contribution guidelines](https://github.com/PitchConnect/contribution-guidelines).

## Table of Contents

- [Quick Start](#quick-start)
- [Code of Conduct](#code-of-conduct)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Project-Specific Guidelines](#project-specific-guidelines)
- [Additional Resources](#additional-resources)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/PitchConnect/match-list-processor.git
cd match-list-processor

# Set up development environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Install pre-commit hooks (if available)
pre-commit install

# Create a feature branch
git checkout develop
git pull
git checkout -b feature/your-feature-name
```

## Code of Conduct

We are committed to providing a welcoming and inclusive experience for everyone. We expect all participants to adhere to our Code of Conduct. Please read the [full Code of Conduct document](https://github.com/PitchConnect/contribution-guidelines/blob/main/CODE_OF_CONDUCT.md) before contributing.

## Development Workflow

This project follows the GitFlow workflow:

### Branch Structure

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: New features or enhancements
- `bugfix/*`: Bug fixes
- `hotfix/*`: Urgent fixes for production
- `release/*`: Release preparation

### Basic Workflow

1. **Create a feature branch from `develop`**
2. **Make your changes with frequent, small commits**
3. **Push your branch and create a Pull Request to `develop`**
4. **Address review feedback**
5. **After approval, your changes will be merged**

For detailed workflow instructions, see our [GitFlow Workflow Guide](https://github.com/PitchConnect/contribution-guidelines/blob/main/workflow.md).

## Pull Request Process

1. **Ensure your code passes all tests and linting checks**
2. **Update documentation if necessary**
3. **Create a Pull Request with a clear description**
4. **Reference any related issues using keywords like "Fixes #123"**
5. **Wait for review and address any feedback**

For detailed PR guidelines, see our [Pull Request Guide](https://github.com/PitchConnect/contribution-guidelines/blob/main/pull-requests.md).

## Coding Standards

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code
- Use 4 spaces for indentation (no tabs)
- Maximum line length of 100 characters
- Use meaningful variable and function names
- Write docstrings for all functions, classes, and modules using Google style
- Use type hints where appropriate
- Run linting and formatting tools before committing

For detailed coding standards, see our [Coding Standards Guide](https://github.com/PitchConnect/contribution-guidelines/blob/main/coding-standards.md).

## Project-Specific Guidelines

### Setup and Installation

1. Make sure you have Docker and Docker Compose installed
2. Create the required Docker volumes:
   ```bash
   docker volume create process-matches-data
   docker volume create google-drive-service-data
   ```
3. Create the Docker network (if not already created):
   ```bash
   docker network create fogis-network
   ```
4. For development, use the provided run script:
   ```bash
   ./run.sh
   ```

### Testing

- Write unit tests for all new functionality
- Use pytest for writing and running tests
- Ensure all tests pass before submitting a pull request
- Include both positive and negative test cases
- Run tests with:
  ```bash
  python -m pytest
  ```

### Special Considerations

- This service interacts with several other microservices in the fogis-network ecosystem
- Changes to API endpoints or data structures may affect other services
- When modifying URL formats or API calls, ensure backward compatibility or coordinate changes with dependent services

## Additional Resources

- [Detailed GitFlow Workflow](https://github.com/PitchConnect/contribution-guidelines/blob/main/workflow.md)
- [Coding Standards](https://github.com/PitchConnect/contribution-guidelines/blob/main/coding-standards.md)
- [Pull Request Guidelines](https://github.com/PitchConnect/contribution-guidelines/blob/main/pull-requests.md)
- [AI Contribution Guidelines](https://github.com/PitchConnect/contribution-guidelines/blob/main/ai-guidelines.md)

## Working with AI Assistants

If you're using AI tools like GitHub Copilot or ChatGPT, or if you are an AI assistant helping with this project, please refer to our [AI Contribution Guidelines](https://github.com/PitchConnect/contribution-guidelines/blob/main/ai-guidelines.md).

## Issue Management

### Creating Issues

- Use descriptive titles that clearly state the problem or feature
- Include detailed descriptions with context and requirements
- Add appropriate labels (see below)
- Reference related issues or PRs
- **Always include a reference to CONTRIBUTING.md** in new issues
  - Add a note like: "Please follow the guidelines in [CONTRIBUTING.md](../CONTRIBUTING.md) when working on this issue"

### Issue Labels

We use the following labels to categorize issues:

- `bug`: Something isn't working as expected
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `question`: Further information is requested
- `wontfix`: This will not be worked on
- `in progress`: Currently being worked on

### Task Tracking

- Use task lists with checkboxes `- [ ]` for tracking progress
- Update these checkboxes as you complete tasks

---

Thank you for contributing to Match List Processor!
