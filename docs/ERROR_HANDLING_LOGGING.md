# Enhanced Error Handling and Logging System

## Overview

The Enhanced Error Handling and Logging system provides comprehensive error management, structured logging, and robust retry mechanisms across all components of the Match List Processor. This system ensures reliable operation, detailed error tracking, and proactive failure recovery.

## Core Components

### 1. Centralized Logging Configuration

**Location**: `src/core/logging_config.py`

The centralized logging system provides:
- **Structured logging** with contextual information
- **Sensitive data filtering** to prevent credential exposure
- **Configurable log levels** and output formats
- **Multi-destination logging** (console, file, external systems)

#### Key Features

**Contextual Formatter**:
- Automatically adds service, component, and timestamp information
- Provides error context for exceptions
- Supports structured log analysis

**Sensitive Data Filter**:
- Automatically masks passwords, tokens, and API keys
- Prevents credential leakage in log files
- Configurable sensitive pattern detection

**Environment-Based Configuration**:
```bash
# Logging configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=custom_format          # Custom log format string
LOG_FILE=match-list-processor.log # Log file name
LOG_DIR=logs                      # Log directory
LOG_ENABLE_CONSOLE=true           # Enable console logging
LOG_ENABLE_FILE=false             # Enable file logging
LOG_ENABLE_STRUCTURED=true        # Enable structured logging
```

### 2. Enhanced Retry Utilities

**Location**: `src/core/retry_utils.py`

The retry system provides:
- **Exponential backoff** with jitter to prevent thundering herd
- **Circuit breaker pattern** for fault tolerance
- **Configurable retry strategies** for different error types
- **Async and sync support** for all retry mechanisms

#### Retry Decorator Usage

**Basic Retry with Exponential Backoff**:
```python
from src.core.retry_utils import retry_with_backoff

@retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=60.0)
def api_call():
    # Your API call here
    return requests.get("https://api.example.com/data")
```

**Async Retry**:
```python
from src.core.retry_utils import async_retry_with_backoff

@async_retry_with_backoff(max_attempts=5, base_delay=2.0)
async def async_api_call():
    # Your async API call here
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/data") as response:
            return await response.json()
```

**Custom Retryable Exceptions**:
```python
import requests
from src.core.retry_utils import retry_with_backoff

@retry_with_backoff(
    max_attempts=3,
    retryable_exceptions=[
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.HTTPError
    ]
)
def selective_retry_call():
    # Only retries on specified exceptions
    return requests.get("https://api.example.com/data")
```

#### Circuit Breaker Usage

**Basic Circuit Breaker**:
```python
from src.core.retry_utils import CircuitBreaker

# Create circuit breaker
cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

@cb
def protected_function():
    # Function protected by circuit breaker
    return external_service_call()
```

**Manual Circuit Breaker**:
```python
cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

try:
    result = cb.call(risky_function, arg1, arg2)
except CircuitBreakerError:
    # Circuit is open, handle gracefully
    return fallback_response()
```

### 3. Enhanced API Client Error Handling

**Location**: `src/services/api_client.py`

The API client includes comprehensive error handling:
- **Contextual error logging** with request details
- **Automatic alert generation** for critical failures
- **Graceful degradation** for service outages
- **Performance monitoring** and slow response detection

#### Error Categories

**Authentication Errors (401)**:
- **Severity**: CRITICAL
- **Action**: Immediate notification to administrators
- **Recovery**: Credential verification and renewal

**Service Errors (500/502/503)**:
- **Severity**: HIGH
- **Action**: Service status monitoring
- **Recovery**: Retry with exponential backoff

**Network Errors**:
- **Severity**: MEDIUM
- **Action**: Network connectivity checks
- **Recovery**: Connection retry and timeout adjustment

**Parsing Errors**:
- **Severity**: MEDIUM
- **Action**: Response format validation
- **Recovery**: API version compatibility check

## Configuration Guide

### Logging Configuration

**Basic Setup**:
```python
from src.core.logging_config import configure_logging, get_logger

# Configure logging with defaults
configure_logging()

# Get logger for your module
logger = get_logger(__name__)

# Use logger
logger.info("Application started")
logger.error("Error occurred", extra={'context': 'additional_info'})
```

**Advanced Configuration**:
```python
from src.core.logging_config import configure_logging

configure_logging(
    log_level="DEBUG",
    enable_console=True,
    enable_file=True,
    enable_structured=True,
    log_file="custom.log",
    log_dir="/var/log/match-processor"
)
```

**Error Context Logging**:
```python
from src.core.logging_config import log_error_context, get_logger

logger = get_logger(__name__)

try:
    risky_operation()
except Exception as e:
    log_error_context(
        logger, e,
        context={
            'user_id': '123',
            'operation': 'data_processing',
            'input_size': len(data)
        },
        operation="process_user_data"
    )
```

### Retry Configuration

**Environment Variables**:
```bash
# Default retry settings
DEFAULT_MAX_ATTEMPTS=3
DEFAULT_BASE_DELAY=1.0
DEFAULT_MAX_DELAY=60.0
DEFAULT_BACKOFF_FACTOR=2.0

# Service-specific retry settings
FOGIS_API_MAX_ATTEMPTS=5
FOGIS_API_BASE_DELAY=2.0
GOOGLE_DRIVE_MAX_ATTEMPTS=3
GOOGLE_DRIVE_BASE_DELAY=1.0
```

**Programmatic Configuration**:
```python
from src.core.retry_utils import retry_with_backoff

# Custom retry configuration
@retry_with_backoff(
    max_attempts=5,
    base_delay=2.0,
    max_delay=120.0,
    backoff_factor=1.5,
    jitter=True,
    on_retry=lambda attempt, error: logger.warning(f"Retry {attempt}: {error}")
)
def custom_retry_function():
    return external_api_call()
```

### Circuit Breaker Configuration

**Service-Level Circuit Breakers**:
```python
from src.core.retry_utils import CircuitBreaker

# Different thresholds for different services
fogis_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
    expected_exception=requests.exceptions.RequestException
)

google_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30.0,
    expected_exception=Exception
)
```

## Error Handling Patterns

### 1. Service Integration Pattern

```python
from src.core.logging_config import get_logger, log_error_context
from src.core.retry_utils import retry_with_backoff, CircuitBreaker

logger = get_logger(__name__)
circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

class ExternalServiceClient:
    @retry_with_backoff(max_attempts=3, base_delay=1.0)
    @circuit_breaker
    def fetch_data(self, endpoint: str) -> dict:
        try:
            response = requests.get(endpoint, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            log_error_context(
                logger, e,
                context={
                    'endpoint': endpoint,
                    'status_code': e.response.status_code if e.response else None,
                    'service': 'external_api'
                },
                operation="fetch_external_data"
            )
            raise

        except Exception as e:
            log_error_context(
                logger, e,
                context={'endpoint': endpoint, 'service': 'external_api'},
                operation="fetch_external_data"
            )
            raise
```

### 2. Graceful Degradation Pattern

```python
from src.core.retry_utils import CircuitBreakerError

def get_user_data(user_id: str) -> dict:
    try:
        # Try primary data source
        return primary_service.get_user(user_id)

    except CircuitBreakerError:
        logger.warning(f"Primary service unavailable, using cache for user {user_id}")
        return cache_service.get_user(user_id)

    except Exception as e:
        log_error_context(
            logger, e,
            context={'user_id': user_id, 'service': 'user_data'},
            operation="get_user_data"
        )
        # Return minimal safe data
        return {'user_id': user_id, 'status': 'unavailable'}
```

### 3. Monitoring Integration Pattern

```python
from src.core.logging_config import get_logger
from src.core.retry_utils import retry_with_backoff

logger = get_logger(__name__)

def on_retry_callback(attempt: int, error: Exception) -> None:
    """Callback for retry attempts to integrate with monitoring."""
    logger.warning(f"Retry attempt {attempt}: {type(error).__name__}: {error}")

    # Send metrics to monitoring system
    metrics.increment('api.retry.attempt', tags={
        'service': 'external_api',
        'error_type': type(error).__name__,
        'attempt': attempt
    })

@retry_with_backoff(
    max_attempts=3,
    base_delay=1.0,
    on_retry=on_retry_callback
)
def monitored_api_call():
    return external_api.fetch_data()
```

## Best Practices

### 1. Logging Best Practices

**Use Structured Logging**:
```python
# Good: Structured logging with context
logger.info("User login successful", extra={
    'user_id': user.id,
    'login_method': 'oauth',
    'ip_address': request.remote_addr
})

# Avoid: String interpolation without structure
logger.info(f"User {user.id} logged in via {method}")
```

**Log at Appropriate Levels**:
- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational information
- **WARNING**: Unexpected but recoverable situations
- **ERROR**: Error conditions that don't stop the application
- **CRITICAL**: Serious errors that may cause the application to stop

**Include Error Context**:
```python
try:
    process_data(data)
except Exception as e:
    log_error_context(
        logger, e,
        context={
            'data_size': len(data),
            'processing_stage': 'validation',
            'user_id': current_user.id
        },
        operation="data_processing"
    )
```

### 2. Retry Best Practices

**Choose Appropriate Retry Strategies**:
- **Exponential backoff**: For rate-limited APIs
- **Fixed delay**: For temporary network issues
- **Immediate retry**: For transient connection errors

**Set Reasonable Limits**:
- **Max attempts**: 3-5 for most operations
- **Max delay**: 60-300 seconds depending on urgency
- **Jitter**: Always enable to prevent thundering herd

**Handle Non-Retryable Errors**:
```python
@retry_with_backoff(
    max_attempts=3,
    retryable_exceptions=[
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout
    ]
)
def api_call():
    # Only retries on connection/timeout errors
    # Authentication errors (401) will not be retried
    return requests.get(url, headers=auth_headers)
```

### 3. Circuit Breaker Best Practices

**Set Appropriate Thresholds**:
- **Failure threshold**: 3-10 failures depending on service criticality
- **Recovery timeout**: 30-300 seconds based on expected recovery time
- **Expected exceptions**: Be specific about which errors trigger the circuit

**Monitor Circuit State**:
```python
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

def monitored_service_call():
    try:
        return circuit_breaker.call(external_service.fetch_data)
    except CircuitBreakerError:
        # Log circuit breaker activation
        logger.warning("Circuit breaker open for external_service")
        metrics.increment('circuit_breaker.open', tags={'service': 'external_service'})
        return fallback_response()
```

## Troubleshooting

### Common Issues

**High Retry Rates**:
- Check network connectivity
- Verify service availability
- Review retry thresholds
- Monitor for cascading failures

**Circuit Breaker Frequently Open**:
- Analyze failure patterns
- Adjust failure threshold
- Implement better error handling
- Add service health checks

**Log Volume Issues**:
- Adjust log levels for production
- Implement log rotation
- Use structured logging for better filtering
- Consider sampling for high-volume operations

### Debugging Tools

**Log Analysis**:
```bash
# Filter logs by error type
grep "ERROR" /var/log/match-processor.log | grep "authentication_failure"

# Analyze retry patterns
grep "Retry attempt" /var/log/match-processor.log | awk '{print $1, $2, $NF}' | sort | uniq -c

# Monitor circuit breaker state
grep "Circuit breaker" /var/log/match-processor.log | tail -20
```

**Performance Monitoring**:
```python
# Add timing to operations
import time
from src.core.logging_config import get_logger

logger = get_logger(__name__)

def timed_operation():
    start_time = time.time()
    try:
        result = expensive_operation()
        duration = time.time() - start_time
        logger.info(f"Operation completed", extra={
            'duration': duration,
            'operation': 'expensive_operation'
        })
        return result
    except Exception as e:
        duration = time.time() - start_time
        log_error_context(
            logger, e,
            context={'duration': duration, 'operation': 'expensive_operation'},
            operation="timed_operation"
        )
        raise
```
