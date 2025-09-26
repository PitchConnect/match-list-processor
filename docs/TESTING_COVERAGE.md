# Test Coverage Requirements

## Overview

This project maintains a **minimum test coverage threshold of 84%** to ensure code quality and reliability. The coverage requirement is enforced through pre-commit hooks and CI/CD pipelines.

## Coverage Enforcement

### Pre-commit Hooks

The project uses pre-commit hooks to validate test coverage before commits:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: coverage-check
      name: Test Coverage Check
      entry: python3 -m pytest --cov=src --cov-fail-under=84 --cov-report=term-missing -q
      language: system
      pass_filenames: false
      stages: [commit]
```

### Running Coverage Checks

```bash
# Run full test suite with coverage
python3 -m pytest --cov=src --cov-report=term-missing

# Run with coverage threshold enforcement
python3 -m pytest --cov=src --cov-fail-under=84 --cov-report=term-missing

# Generate HTML coverage report
python3 -m pytest --cov=src --cov-report=html
# View report: open htmlcov/index.html
```

## Current Coverage Status

**Overall Coverage: 83.50%** (Target: 84%+)

### Module Coverage Breakdown

| Module | Coverage | Status | Priority |
|--------|----------|--------|----------|
| `redis_integration/config.py` | 100% | ✅ Excellent | - |
| `redis_integration/message_formatter.py` | 97% | ✅ Excellent | - |
| `redis_integration/services.py` | 92% | ✅ Good | - |
| `redis_integration/connection_manager.py` | 84% | ✅ Good | - |
| `redis_integration/app_integration.py` | 73% | ⚠️ Needs improvement | High |
| `redis_integration/publisher.py` | 43% | ❌ Low | High |

### Areas Needing Improvement

1. **Redis Publisher** (43% coverage)
   - Missing tests for error handling paths
   - Need tests for Redis connection failures
   - Missing multi-version publishing edge cases

2. **App Integration** (73% coverage)
   - Error handling in Enhanced Schema v2.0 processing
   - Fallback mechanism testing
   - Organization ID validation edge cases

## Adding Test Coverage

### Identifying Coverage Gaps

```bash
# Generate detailed coverage report
python3 -m pytest --cov=src --cov-report=term-missing

# Look for "Missing" lines in the output
# Example:
# src/redis_integration/publisher.py    43%   84-88, 110-140, 168-239
```

### Writing Effective Tests

1. **Focus on Critical Paths**
   - Error handling and exception paths
   - Edge cases and boundary conditions
   - Integration points between modules

2. **Test Structure**
   ```python
   class TestModuleCoverage(unittest.TestCase):
       """Test module for improved coverage."""
       
       def test_error_handling(self):
           """Test error handling paths."""
           # Test exception scenarios
           
       def test_edge_cases(self):
           """Test boundary conditions."""
           # Test edge cases
           
       def test_disabled_state(self):
           """Test behavior when features are disabled."""
           # Test disabled configurations
   ```

3. **Coverage Targets**
   - **New modules**: 90%+ coverage required
   - **Modified modules**: Must not decrease existing coverage
   - **Critical modules**: 95%+ coverage recommended

### Testing Best Practices

1. **Mock External Dependencies**
   ```python
   @patch('redis_integration.connection_manager.redis.from_url')
   def test_redis_connection_failure(self, mock_redis):
       mock_redis.side_effect = Exception("Connection failed")
       # Test error handling
   ```

2. **Test Configuration Variations**
   ```python
   def test_disabled_feature(self):
       self.service.config.enabled = False
       result = self.service.some_method()
       self.assertTrue(result)  # Should handle gracefully
   ```

3. **Test Error Conditions**
   ```python
   def test_invalid_input(self):
       with self.assertRaises(ValueError):
           self.formatter.format_message(None)
   ```

## Coverage Improvement Strategy

### Phase 1: Quick Wins (Target: 84%+)
- Add tests for disabled state handling
- Test configuration edge cases
- Add error handling tests

### Phase 2: Comprehensive Coverage (Target: 90%+)
- Complete Redis publisher testing
- Add integration test scenarios
- Test all error paths

### Phase 3: Excellence (Target: 95%+)
- Performance testing
- Stress testing
- Complete edge case coverage

## Troubleshooting Coverage Issues

### Common Issues

1. **Coverage Below Threshold**
   ```bash
   FAIL Required test coverage of 84% not reached. Total coverage: 83.50%
   ```
   **Solution**: Add tests for uncovered lines shown in the report.

2. **Pre-commit Hook Failures**
   ```bash
   Test Coverage Check......................Failed
   ```
   **Solution**: Run coverage locally and fix gaps before committing.

3. **Flaky Coverage Results**
   **Solution**: Ensure tests are deterministic and don't depend on external state.

### Getting Help

1. **View Detailed Coverage Report**
   ```bash
   python3 -m pytest --cov=src --cov-report=html
   open htmlcov/index.html
   ```

2. **Identify Specific Missing Lines**
   ```bash
   python3 -m pytest --cov=src --cov-report=term-missing | grep "Missing"
   ```

3. **Test Specific Modules**
   ```bash
   python3 -m pytest tests/redis_integration/ --cov=src/redis_integration --cov-report=term-missing
   ```

## Contributing Guidelines

### Before Submitting PRs

1. ✅ Run full test suite with coverage
2. ✅ Ensure coverage meets 84% minimum
3. ✅ Add tests for new functionality
4. ✅ Test error handling paths
5. ✅ Update documentation if needed

### PR Review Checklist

- [ ] All tests pass
- [ ] Coverage threshold met (84%+)
- [ ] New code has appropriate test coverage
- [ ] Error handling tested
- [ ] Documentation updated

## Continuous Improvement

The coverage threshold may be increased over time as the codebase matures:

- **Current**: 84% minimum
- **Target**: 90% by next major release
- **Goal**: 95% for critical modules

Regular coverage reviews help identify areas for improvement and ensure long-term code quality.
