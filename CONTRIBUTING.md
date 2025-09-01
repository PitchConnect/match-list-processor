# Contributing to FOGIS Match List Processor

**Version: 2.0.0 (Phase 1B Consolidated Service)**
**Updated: 2025-08-31**

Thank you for considering contributing to the FOGIS Match List Processor! This document provides essential guidelines for contributing to the unified service with enhanced change detection capabilities.

## 🎯 Project Overview

The FOGIS Match List Processor is a **consolidated service** that provides:

- **🔍 Enhanced Change Detection**: 11 granular change categories with priority assessment
- **⚡ Unified Processing**: Single service architecture with integrated change detection
- **🎨 Asset Generation**: WhatsApp descriptions and team avatars
- **☁️ Cloud Integration**: Google Drive and calendar sync capabilities
- **🏥 Health Monitoring**: Comprehensive service monitoring and validation

## 📋 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [📜 Code of Conduct](#-code-of-conduct)
- [🔄 Development Workflow](#-development-workflow)
- [🔧 Development Environment](#-development-environment)
- [🧪 Testing Requirements](#-testing-requirements)
- [📝 Pull Request Process](#-pull-request-process)
- [🎨 Coding Standards](#-coding-standards)
- [🏗️ Architecture Guidelines](#️-architecture-guidelines)
- [🤖 Working with AI Assistants](#-working-with-ai-assistants)
- [📊 Issue Management](#-issue-management)
- [📚 Additional Resources](#-additional-resources)

## 🚀 Quick Start

### Development Setup

```bash
# Clone the repository
git clone https://github.com/PitchConnect/match-list-processor.git
cd match-list-processor

# Set up Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run comprehensive test suite
python -m pytest tests/ --cov=src --cov-report=html

# Validate code quality
pre-commit run --all-files

# Create feature branch
git checkout -b feature/your-feature-name
```

### Docker Development

```bash
# Start development environment
./run.sh

# Or start with Docker Compose
docker compose up -d

# Run tests in container
docker compose exec process-matches-service python -m pytest

# Validate deployment
./scripts/validate_deployment.sh
```

## 📜 Code of Conduct

We are committed to providing a welcoming and inclusive experience for everyone. We expect all participants to adhere to our Code of Conduct. Please read the [full Code of Conduct document](https://github.com/PitchConnect/contribution-guidelines/blob/main/CODE_OF_CONDUCT.md) before contributing.

## 🔄 Development Workflow

### Branch Strategy

This project uses a **simplified branching model** for the consolidated service:

- **`main`**: Production-ready code (Phase 1B consolidated service)
- **`feature/*`**: New features and enhancements
- **`bugfix/*`**: Bug fixes and patches
- **`hotfix/*`**: Critical production fixes

### Development Process

1. **🍴 Fork and Clone**: Fork the repository and clone your fork
2. **🌿 Create Branch**: Create a feature branch from `main`
3. **💻 Develop**: Implement your changes with comprehensive tests
4. **🧪 Test**: Ensure all 200+ tests pass with 95%+ coverage
5. **🎨 Quality Check**: Run pre-commit hooks and code quality tools
6. **📝 Document**: Update documentation for your changes
7. **🔄 Pull Request**: Submit PR with detailed description
8. **👀 Review**: Address feedback and ensure CI passes
9. **🚀 Merge**: Maintainer merges after approval

### Commit Message Format

Use conventional commits for clear history:

```
type(scope): description

feat(change-detection): add granular referee change categorization
fix(health-check): resolve timeout issues with external services
docs(api): update endpoint documentation for Phase 1B
test(integration): add comprehensive change categorization tests
```

**Types:**
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation updates
- `test`: Test additions/updates
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `ci`: CI/CD changes
- `bugfix/*`: Bug fixes
- `hotfix/*`: Urgent fixes for production
- `release/*`: Release preparation

## 🔧 Development Environment

### Prerequisites

- **Python 3.11+** (required for unified processor)
- **Docker Engine 20.10+** and **Docker Compose 2.0+**
- **Git** for version control
- **curl** for API testing

### Local Development Setup

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Configure environment
cp .env.example .env
# Edit .env with development settings

# Start external services (if needed)
docker network create fogis-network
docker volume create process-matches-data
```

## 🧪 Testing Requirements

### Test Categories

The project maintains **200+ tests** across multiple categories:

- **🔍 Change Detection Tests**: Granular change categorization (29 tests)
- **⚙️ Unified Processor Tests**: Core processing engine (45 tests)
- **🎨 Asset Generation Tests**: WhatsApp descriptions and avatars (32 tests)
- **🏥 Health Check Tests**: Service monitoring (18 tests)
- **🔧 Integration Tests**: External service integration (28 tests)

### Quality Standards

- **✅ 100% Test Success Rate**: All tests must pass
- **📊 95%+ Code Coverage**: Comprehensive test coverage required
- **🔒 Security Compliance**: Pass bandit security scans
- **📝 Type Safety**: Full mypy type checking compliance

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run specific test categories
python -m pytest tests/test_change_categorization.py
python -m pytest tests/test_unified_processor.py

# Run tests with verbose output
python -m pytest -v --timeout=30
```

## 📝 Pull Request Process

### Before Submitting

1. **✅ All Tests Pass**: Run `python -m pytest` successfully
2. **📊 Coverage Maintained**: Ensure 95%+ test coverage
3. **🎨 Code Quality**: Run `pre-commit run --all-files`
4. **📚 Documentation**: Update docs for new features
5. **🔧 Deployment Validation**: Run `./scripts/validate_deployment.sh`

### ⚠️ MANDATORY: Issue Reference Requirements

**Every PR must properly reference all issues it resolves** to ensure automatic closure and accurate milestone tracking.

#### Required Format

Use these exact keywords in your PR description:

- `Fixes #123` - Closes issue #123 when PR is merged
- `Closes #456` - Closes issue #456 when PR is merged
- `Resolves #789` - Closes issue #789 when PR is merged

#### Issue Reference Checklist

Before submitting your PR, verify:

- [ ] **Primary Issue Referenced**: Main issue addressed by this PR
- [ ] **All Resolved Issues Listed**: Every issue this PR fully resolves
- [ ] **Cross-Reference Check**: Reviewed open issues to identify additional closures
- [ ] **Acceptance Criteria Met**: All requirements from referenced issues satisfied
- [ ] **No Partial Implementations**: Issues only referenced if completely resolved

#### Common Mistakes to Avoid

❌ **Don't do this:**
```markdown
Related to #123
See #456
Addresses #789
```

✅ **Do this instead:**
```markdown
Fixes #123
Closes #456
Resolves #789
```

### PR Requirements

1. **Clear Description**: Explain what changes and why
2. **Proper Issue References**: Use "Fixes #X" format for all resolved issues
3. **Test Evidence**: Include test results and coverage reports
4. **Breaking Changes**: Document any breaking changes
5. **Migration Notes**: Include migration steps if needed

### Multi-Issue PRs

When your PR resolves multiple issues:

1. **List all resolved issues** in the PR description
2. **Verify each issue is completely addressed**
3. **Consider breaking large PRs** into smaller, focused changes
4. **Document the relationship** between issues if complex

### Review Process

#### Reviewer Responsibilities

Reviewers must verify:

##### Issue Closure Verification
- [ ] **All resolved issues properly referenced** with "Fixes #X" format
- [ ] **Implementation addresses all acceptance criteria**
- [ ] **No additional issues resolved** without proper references
- [ ] **Automatic closure will work** upon merge

##### Code Quality Review
- [ ] **Code follows project conventions**
- [ ] **Tests provide adequate coverage**
- [ ] **Documentation is complete**
- [ ] **Security considerations addressed**
- [ ] **Performance impact acceptable**

#### Review Steps

1. **Automated Checks**: CI pipeline must pass
2. **Issue Reference Verification**: Confirm all resolved issues are properly referenced
3. **Code Review**: At least one maintainer approval
4. **Testing**: Reviewer validates functionality
5. **Documentation**: Verify docs are updated
6. **Merge**: Maintainer merges after approval

## 📅 Milestone Audit Process

### Monthly Milestone Review

To ensure accurate milestone tracking and prevent missed issue closures, we conduct monthly milestone audits.

#### Audit Schedule
- **Frequency**: First week of each month
- **Responsibility**: Project maintainer or designated reviewer
- **Duration**: 1-2 hours depending on milestone size

#### Audit Steps

1. **Review Open Issues**
   ```bash
   # List all open issues in current milestone
   gh issue list --milestone "Current Milestone" --state open
   ```

2. **Cross-Reference Recent PRs**
   ```bash
   # List recently merged PRs
   gh pr list --state merged --limit 20
   ```

3. **Identify Missed Closures**
   - Compare implemented functionality with open issue requirements
   - Look for PRs that resolve issues without proper "Fixes #X" references
   - Check if acceptance criteria from open issues are met by merged code

4. **Update Issue Status**
   - Close resolved issues with explanatory comments
   - Update issue descriptions if partially resolved
   - Add proper cross-references between related issues

#### Preventing Future Missed Closures

**For Contributors:**
- Always use "Fixes #X" format in PR descriptions
- Review open issues before submitting PRs
- Cross-reference your implementation with issue requirements

**For Reviewers:**
- Verify all resolved issues are properly referenced
- Check if PR resolves additional unreferenced issues
- Confirm automatic closure will work upon merge

**For Maintainers:**
- Conduct regular milestone audits
- Update PR and review templates as needed
- Train team on proper issue reference practices

## 🎨 Coding Standards

### Python Code Style

- **📏 PEP 8 Compliance**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) guidelines
- **🔤 Indentation**: Use 4 spaces (no tabs)
- **📐 Line Length**: Maximum 100 characters
- **📝 Naming**: Use meaningful, descriptive names
- **📚 Docstrings**: Google-style docstrings for all public functions/classes
- **🔍 Type Hints**: Use type hints for function parameters and returns
- **🎨 Formatting**: Automatic Black formatting enforced

### Code Quality Tools

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Security scanning
bandit -r src/

# Run all quality checks
pre-commit run --all-files
```

### Documentation Standards

- **📖 Code Comments**: Explain complex logic and business rules
- **📝 Docstrings**: Document all public APIs with examples
- **📋 README Updates**: Update README for new features
- **🔧 Configuration Docs**: Document new environment variables
- **🧪 Test Documentation**: Explain test scenarios and edge cases

## 🏗️ Architecture Guidelines

### Unified Service Architecture

The service follows a **consolidated architecture** with these principles:

- **🎯 Single Responsibility**: Each module has a clear, focused purpose
- **🔌 Dependency Injection**: Use interfaces for external dependencies
- **🧪 Testability**: Design for easy unit and integration testing
- **📊 Observability**: Include logging, metrics, and health checks
- **🔧 Configuration**: Environment-based configuration management

### Module Structure

```
src/
├── core/                    # Core business logic
│   ├── change_categorization.py    # Enhanced change detection
│   ├── unified_processor.py        # Main processing engine
│   └── match_processor.py          # Match processing logic
├── services/                # External service integrations
│   ├── api_client.py               # FOGIS API client
│   ├── calendar_sync.py            # Calendar integration
│   └── asset_generator.py          # Asset generation
├── utils/                   # Utility functions
│   ├── file_operations.py          # File handling
│   └── description_generator.py    # Text generation
├── web/                     # Web interface
│   └── health_server.py            # Health check endpoints
└── app_unified.py          # Main application entry point
```

### Design Patterns

- **🏭 Factory Pattern**: For creating service instances
- **🎯 Strategy Pattern**: For different processing modes
- **👀 Observer Pattern**: For change notifications
- **🔧 Builder Pattern**: For complex configuration objects
- **🛡️ Circuit Breaker**: For external service resilience

### Change Detection Guidelines

When working with the enhanced change detection system:

```python
# Example: Adding a new change category
class NewChangeAnalyzer(FieldChangeAnalyzer):
    def analyze_field_changes(self, prev_match: Dict, curr_match: Dict) -> List[MatchChangeDetail]:
        changes = []

        # Implement specific change detection logic
        if self._detect_new_change_type(prev_match, curr_match):
            changes.append(MatchChangeDetail(
                match_id=curr_match['matchid'],
                change_category=ChangeCategory.NEW_TYPE,
                priority=self._assess_priority(prev_match, curr_match),
                affected_stakeholders=self._determine_stakeholders(),
                change_description=self._generate_description(prev_match, curr_match),
                timestamp=datetime.utcnow()
            ))

        return changes
```

### Error Handling

- **🛡️ Graceful Degradation**: Service continues with partial functionality
- **🔄 Retry Logic**: Implement exponential backoff for transient failures
- **📊 Error Logging**: Structured logging with context information
- **🚨 Alerting**: Clear error messages for monitoring systems
- **🔧 Recovery**: Automatic recovery mechanisms where possible

## 🤖 Working with AI Assistants

### For Human Contributors Using AI

- **🔍 Review Thoroughly**: Review all AI-generated code carefully
- **📝 Disclose Usage**: Mention AI assistance in PR descriptions
- **🧠 Think Critically**: Don't blindly trust AI output
- **🛠️ Use as Tool**: AI assists, humans decide and validate

### For AI Assistants

When contributing to this project:

1. **📚 Read Documentation**: Understand the unified architecture and Phase 1B changes
2. **🔍 Analyze Codebase**: Review existing change categorization and unified processor code
3. **📋 Follow Conventions**: Use established patterns and coding standards
4. **🧪 Include Tests**: Write comprehensive tests for new functionality
5. **📝 Document Changes**: Update documentation for new features
6. **🏷️ Use Prefixes**: Use `[AI]` prefix in commit messages

### AI Contribution Guidelines

- **Understand the consolidated service architecture**
- **Follow the enhanced change detection patterns**
- **Maintain the 200+ test suite quality standards**
- **Respect the unified processor design principles**
- **Document Phase 1B specific features and capabilities**

## 📊 Issue Management

### Creating Issues

Use descriptive titles and detailed descriptions:

```markdown
## 🎯 Objective
Clear description of the issue or feature

## 📋 Acceptance Criteria
- [ ] Specific, measurable requirements
- [ ] Test coverage requirements
- [ ] Documentation updates needed

## 🔧 Technical Specifications
Implementation details and constraints

## 🧪 Testing Requirements
Test scenarios and validation criteria
```

### Issue Labels

**Phase 1B Specific Labels:**
- `phase-1b`: Related to consolidated service architecture
- `change-detection`: Enhanced change categorization features
- `unified-processor`: Core processing engine improvements
- `documentation`: Phase 1B documentation updates

**General Labels:**
- `bug`: Something isn't working as expected
- `enhancement`: New feature or request
- `good-first-issue`: Good for newcomers
- `help-wanted`: Extra attention needed

### Task Tracking

- Use task lists with checkboxes `- [ ]` for progress tracking
- Update checkboxes as tasks complete
- Reference related issues with `Fixes #123` or `Related to #456`

## 📚 Additional Resources

### Phase 1B Documentation

- **[DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Comprehensive deployment instructions
- **[API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)** - Complete API reference
- **[MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)** - Migration from webhook architecture
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[PHASE_1B_VERIFICATION.md](PHASE_1B_VERIFICATION.md)** - Implementation verification

### External Resources

- **[PitchConnect Contribution Guidelines](https://github.com/PitchConnect/contribution-guidelines)**
- **[GitFlow Workflow Guide](https://github.com/PitchConnect/contribution-guidelines/blob/main/workflow.md)**
- **[Coding Standards](https://github.com/PitchConnect/contribution-guidelines/blob/main/coding-standards.md)**
- **[AI Contribution Guidelines](https://github.com/PitchConnect/contribution-guidelines/blob/main/ai-guidelines.md)**

### Development Tools

- **[Docker Documentation](https://docs.docker.com/)**
- **[pytest Documentation](https://docs.pytest.org/)**
- **[Black Code Formatter](https://black.readthedocs.io/)**
- **[mypy Type Checker](https://mypy.readthedocs.io/)**

## 🎯 Phase 1B Specific Guidelines

### Enhanced Change Detection

When working with the change categorization system:

```python
# Example: Contributing to change detection
from src.core.change_categorization import ChangeCategory, ChangePriority

# Always use the established enums
change_detail = MatchChangeDetail(
    change_category=ChangeCategory.REFEREE_CHANGE,
    priority=ChangePriority.HIGH,
    affected_stakeholders=[StakeholderType.REFEREES]
)
```

### Unified Processor Integration

- **Maintain single service architecture** - No external webhook dependencies
- **Preserve all 200+ tests** - Ensure comprehensive test coverage
- **Follow unified processing patterns** - Use established processing cycles
- **Document configuration changes** - Update environment variable docs

### Configuration Management

- **Use environment variables** for all configuration
- **Update .env.example** for new variables
- **Validate with deployment script** - Run `./scripts/validate_deployment.sh`
- **Document in deployment guide** - Update relevant documentation

---

**🎯 Contributing to FOGIS Match List Processor v2.0.0**
*Phase 1B Consolidated Service with Enhanced Change Detection*

Thank you for contributing to the unified match processing service! Your contributions help improve football match management for referees and coordinators.

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
