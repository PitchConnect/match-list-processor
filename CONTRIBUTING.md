# Contributing to Match List Processor

Thank you for considering contributing to Match List Processor! This document provides essential guidelines for contributing to this project. For more detailed information, please refer to our [comprehensive contribution guidelines](https://github.com/PitchConnect/contribution-guidelines).

## Table of Contents

- [Quick Start](#quick-start)
- [Code of Conduct](#code-of-conduct)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Project-Specific Guidelines](#project-specific-guidelines)
- [Working with AI Assistants](#working-with-ai-assistants)
- [Issue Management](#issue-management)
- [Additional Resources](#additional-resources)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/PitchConnect/match-list-processor.git
cd match-list-processor

# Set up development environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Install pre-commit hooks
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

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality and consistency. The hooks automatically run the same checks as our CI/CD pipeline locally before you commit.

#### Installation

Pre-commit hooks are automatically installed when you run the quick start setup. If you need to install them manually:

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Install the hooks for this repository
pre-commit install
```

#### What the hooks check

Our pre-commit configuration includes:

- **Code formatting**: Black automatically formats your Python code
- **Import sorting**: isort organizes your imports consistently
- **Linting**: flake8 checks for code style and potential issues
- **Type checking**: mypy verifies type annotations (src/ directory only)
- **Security scanning**: bandit scans for common security issues
- **General checks**: trailing whitespace, file endings, YAML syntax, etc.

#### Running hooks manually

You can run the hooks manually at any time:

```bash
# Run hooks on all files
pre-commit run --all-files

# Run hooks on staged files only
pre-commit run

# Run a specific hook
pre-commit run black
pre-commit run flake8
pre-commit run mypy
```

#### Troubleshooting

If pre-commit hooks fail:

1. **Read the error messages carefully** - they usually tell you exactly what's wrong
2. **Let the hooks fix what they can** - Black and isort will automatically fix formatting
3. **Fix remaining issues manually** - Address any linting or type errors
4. **Re-run the hooks** to verify fixes
5. **Commit your changes** once all hooks pass

The hooks are designed to catch the same issues that would fail in CI/CD, saving you time and ensuring consistent code quality.

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

## Working with AI Assistants

If you're using AI tools like GitHub Copilot or ChatGPT, or if you are an AI assistant helping with this project, please follow these guidelines:

### For Human Contributors Using AI

- Review all AI-generated code thoroughly
- Disclose AI usage in your PR description
- Don't blindly trust AI output
- Use AI as a tool, not a replacement

### For AI Assistants

- Read project documentation first
- Understand the codebase before making changes
- Follow project conventions
- Plan before coding
- Document your process
- Use the "[AI]" prefix in commit messages

For complete AI contribution guidelines, see our [AI Contribution Guidelines](https://github.com/PitchConnect/contribution-guidelines/blob/main/ai-guidelines.md).

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
- If you're an AI assistant, remind users to update task checkboxes

## Additional Resources

- [Detailed GitFlow Workflow](https://github.com/PitchConnect/contribution-guidelines/blob/main/workflow.md)
- [Coding Standards](https://github.com/PitchConnect/contribution-guidelines/blob/main/coding-standards.md)
- [Pull Request Guidelines](https://github.com/PitchConnect/contribution-guidelines/blob/main/pull-requests.md)
- [AI Contribution Guidelines](https://github.com/PitchConnect/contribution-guidelines/blob/main/ai-guidelines.md)

---

Thank you for contributing to Match List Processor!
