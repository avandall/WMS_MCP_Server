# Error Handling Guide

## Overview

The WMS MCP Server uses a comprehensive error handling system to provide clear, actionable error information to clients. All errors follow a consistent format and include error codes for programmatic handling.

## Error Response Format

All error responses follow this standard structure:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "Additional context-specific information"
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Always `false` for error responses |
| error | string | Human-readable error message |
| error_code | string | Machine-readable error code for programmatic handling |
| details | object | Optional additional context for debugging |

## Error Codes

### Client Errors (4xx)

| Error Code | HTTP Status | Description | Common Causes |
|-------------|-------------|-------------|----------------|
| VALIDATION_ERROR | 400 | Invalid input parameters | Missing required fields, invalid data types, format errors |
| NOT_FOUND | 404 | Resource not found | Invalid SKU, order ID, or location code |
| INSUFFICIENT_STOCK | 400 | Not enough inventory for operation | Attempting to move/update more stock than available |
| INSUFFICIENT_CAPACITY | 400 | No storage space available | Location at full capacity |
| LOCK_ACQUISITION_FAILED | 409 | Could not acquire distributed lock | Concurrent operation in progress |
| UNAUTHORIZED | 401 | Missing or invalid authentication | Invalid or missing API key |
| FORBIDDEN | 403 | Insufficient permissions | User lacks required role/permission |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests | Exceeded rate limit for tool category |

### Server Errors (5xx)

| Error Code | HTTP Status | Description | Common Causes |
|-------------|-------------|-------------|----------------|
| DATABASE_ERROR | 500 | Database operation failed | Connection issues, query errors, constraints |
| REDIS_ERROR | 500 | Redis operation failed | Connection issues, cache errors |
| QUEUE_ERROR | 500 | Message queue operation failed | RabbitMQ/Kafka connection issues |
| INTERNAL_ERROR | 500 | Unexpected server error | Unhandled exceptions, system failures |

## Error Handling Strategies

### 1. Validation Errors (VALIDATION_ERROR)

**When to expect**: Invalid or missing input parameters

**Handling Strategy**:
```python
try:
    result = await session.call_tool("check_stock_availability", {
        "sku_code": ""  # Invalid empty string
    })
except Exception as e:
    if e.error_code == "VALIDATION_ERROR":
        # Log the validation error
        logger.error(f"Validation failed: {e.error}")
        # Prompt user for correct input
        return "Please provide a valid SKU code"
```

**Prevention**:
- Validate all inputs before calling tools
- Use Pydantic models for input validation
- Check required fields are present
- Verify data types match expected formats

### 2. Not Found Errors (NOT_FOUND)

**When to expect**: Requested resource doesn't exist

**Handling Strategy**:
```python
result = await session.call_tool("check_stock_availability", {
    "sku_code": "NONEXISTENT-SKU"
})

if not result.success and result.error_code == "NOT_FOUND":
    # Resource doesn't exist
    logger.warning(f"SKU not found: {result.error}")
    # Offer to create or suggest alternatives
    return "SKU not found. Would you like to check a different SKU?"
```

**Prevention**:
- Verify resource existence before operations
- Use lookup tools to validate IDs
- Implement fuzzy matching for user inputs

### 3. Lock Acquisition Errors (LOCK_ACQUISITION_FAILED)

**When to expect**: Concurrent operation in progress on same resource

**Handling Strategy**:
```python
max_retries = 3
retry_delay = 1  # seconds

for attempt in range(max_retries):
    result = await session.call_tool("update_inventory_quantity", {
        "sku_code": "SKU-1060-6GB",
        "location_code": "ZONE-A-ROW-02-SHELF-01",
        "action": "INCREASE",
        "quantity": 10
    })
    
    if result.success:
        break
    
    if result.error_code == "LOCK_ACQUISITION_FAILED":
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            continue
        else:
            # Max retries reached
            logger.error(f"Failed to acquire lock after {max_retries} attempts")
            return "Operation in progress. Please try again later."
```

**Prevention**:
- Implement retry logic with exponential backoff
- Use appropriate lock timeouts
- Monitor lock contention
- Consider batching operations to reduce lock frequency

### 4. Database Errors (DATABASE_ERROR)

**When to expect**: Database connection or query failures

**Handling Strategy**:
```python
result = await session.call_tool("get_order_status_details", {
    "order_id": "ORDER-2024-00890"
})

if not result.success and result.error_code == "DATABASE_ERROR":
    # Log database error for monitoring
    logger.error(f"Database error: {result.error}")
    
    # Check if it's a transient error
    if "connection" in result.error.lower():
        # Retry with backoff
        return await retry_with_backoff(operation)
    else:
        # Non-transient error - alert
        await create_system_alert("CRITICAL", f"Database error: {result.error}")
        return "System error. Please contact support."
```

**Prevention**:
- Implement connection pooling
- Use database health checks
- Monitor query performance
- Implement circuit breakers for repeated failures

### 5. Redis Errors (REDIS_ERROR)

**When to expect**: Cache or lock service failures

**Handling Strategy**:
```python
result = await session.call_tool("check_redis_locks", {
    "resource_key": "lock:sku:SKU-1060-6GB"
})

if not result.success and result.error_code == "REDIS_ERROR":
    # Fallback to direct database check
    logger.warning(f"Redis unavailable, using fallback: {result.error}")
    return await check_lock_in_database(resource_key)
```

**Prevention**:
- Implement Redis health monitoring
- Use fallback mechanisms when Redis is unavailable
- Monitor Redis memory usage
- Implement Redis clustering for high availability

### 6. Insufficient Stock Errors (INSUFFICIENT_STOCK)

**When to expect**: Attempting operations beyond available inventory

**Handling Strategy**:
```python
result = await session.call_tool("update_inventory_quantity", {
    "sku_code": "SKU-1060-6GB",
    "location_code": "ZONE-A-ROW-02-SHELF-01",
    "action": "DECREASE",
    "quantity": 100  # More than available
})

if not result.success and result.error_code == "INSUFFICIENT_STOCK":
    available = result.details.get('available_quantity', 0)
    logger.warning(f"Insufficient stock. Available: {available}")
    return f"Only {available} units available. Please reduce quantity."
```

**Prevention**:
- Check stock availability before operations
- Use `check_stock_availability` tool first
- Implement reservation systems for high-demand items
- Monitor low stock alerts

### 7. Rate Limit Errors (RATE_LIMIT_EXCEEDED)

**When to expect**: Exceeded request rate limits

**Handling Strategy**:
```python
result = await session.call_tool("check_stock_availability", {
    "sku_code": "SKU-1060-6GB"
})

if not result.success and result.error_code == "RATE_LIMIT_EXCEEDED":
    # Extract retry information from headers
    retry_after = result.headers.get('X-RateLimit-Reset', 60)
    logger.warning(f"Rate limited. Retry after {retry_after} seconds")
    
    # Implement client-side rate limiting
    await asyncio.sleep(int(retry_after))
    return await retry_operation()
```

**Prevention**:
- Implement client-side rate limiting
- Use caching for read operations
- Batch requests when possible
- Monitor rate limit headers

## Retry Strategies

### Exponential Backoff

```python
import asyncio

async def retry_with_backoff(operation, max_retries=3, base_delay=1):
    """Retry operation with exponential backoff"""
    for attempt in range(max_retries):
        try:
            result = await operation()
            if result.success:
                return result
            
            # Don't retry non-transient errors
            if result.error_code in ["VALIDATION_ERROR", "NOT_FOUND", "FORBIDDEN"]:
                return result
                
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt)  # Exponential backoff
            await asyncio.sleep(delay)
    
    return None  # All retries failed
```

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, operation):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await operation()
            if result.success:
                self.failure_count = 0
                self.state = "CLOSED"
                return result
            else:
                self._handle_failure()
                return result
        except Exception as e:
            self._handle_failure()
            raise
    
    def _handle_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
```

## Logging and Monitoring

### Structured Error Logging

```python
import json
import logging

logger = logging.getLogger(__name__)

def log_error(error_response, context=None):
    """Log error with structured format"""
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "error_code": error_response.error_code,
        "error_message": error_response.error,
        "context": context or {},
        "details": error_response.details
    }
    logger.error(json.dumps(log_data))
```

### Error Metrics

Track these metrics for monitoring:
- Error rate by error code
- Error rate by tool
- Retry success rate
- Average time to recovery
- Circuit breaker state changes

## Best Practices

### 1. Always Check Success Status

```python
# Good
result = await session.call_tool("check_stock_availability", {"sku_code": "SKU-001"})
if not result.success:
    handle_error(result)

# Bad - assumes success
result = await session.call_tool("check_stock_availability", {"sku_code": "SKU-001"})
data = result.data  # May fail if result.success is False
```

### 2. Use Specific Error Code Handling

```python
# Good
if result.error_code == "LOCK_ACQUISITION_FAILED":
    await retry_with_backoff(operation)
elif result.error_code == "VALIDATION_ERROR":
    fix_input_validation()
elif result.error_code == "NOT_FOUND":
    handle_missing_resource()

# Bad - generic handling
if not result.success:
    await retry_with_backoff(operation)  # Retries validation errors
```

### 3. Implement Graceful Degradation

```python
async def get_with_cache(sku_code):
    """Try cache first, fallback to database"""
    try:
        result = await session.call_tool("check_stock_availability", {
            "sku_code": sku_code,
            "use_cache": True
        })
        if result.success:
            return result
    except Exception as e:
        logger.warning(f"Cache failed, using database: {e}")
    
    # Fallback to database
    return await session.call_tool("check_stock_availability", {
        "sku_code": sku_code,
        "use_cache": False
    })
```

### 4. Provide User-Friendly Messages

```python
def get_user_message(error_response):
    """Convert technical error to user-friendly message"""
    messages = {
        "VALIDATION_ERROR": "Please check your input and try again",
        "NOT_FOUND": "The requested resource was not found",
        "LOCK_ACQUISITION_FAILED": "Another operation is in progress. Please wait and try again",
        "INSUFFICIENT_STOCK": "Not enough inventory available",
        "RATE_LIMIT_EXCEEDED": "Too many requests. Please wait and try again",
        "DATABASE_ERROR": "System error. Please try again later",
        "REDIS_ERROR": "System error. Please try again later"
    }
    return messages.get(error_response.error_code, "An error occurred. Please try again")
```

## Testing Error Handling

### Unit Test Example

```python
import pytest

async def test_lock_acquisition_retry():
    """Test retry logic for lock acquisition failures"""
    mock_tool = MockTool()
    mock_tool.set_error("LOCK_ACQUISITION_FAILED", count=2)
    
    result = await retry_with_backoff(
        lambda: mock_tool.execute(),
        max_retries=3
    )
    
    assert result.success
    assert mock_tool.call_count == 3  # 2 failures + 1 success
```

### Integration Test Example

```python
async def test_insufficient_stock_handling():
    """Test insufficient stock error handling"""
    # First, check available stock
    stock_result = await session.call_tool("check_stock_availability", {
        "sku_code": "SKU-1060-6GB"
    })
    available = stock_result.data["available_quantity"]
    
    # Try to decrease more than available
    result = await session.call_tool("update_inventory_quantity", {
        "sku_code": "SKU-1060-6GB",
        "location_code": "ZONE-A-ROW-02-SHELF-01",
        "action": "DECREASE",
        "quantity": available + 100
    })
    
    assert not result.success
    assert result.error_code == "INSUFFICIENT_STOCK"
    assert "available_quantity" in result.details
```

## Alerting

### Critical Error Alerts

Create system alerts for critical errors:

```python
async def handle_critical_error(error_response):
    """Handle critical errors with alerts"""
    critical_codes = ["DATABASE_ERROR", "REDIS_ERROR", "QUEUE_ERROR"]
    
    if error_response.error_code in critical_codes:
        await session.call_tool("create_system_alert", {
            "alert_type": "CRITICAL",
            "message": f"Critical system error: {error_response.error_code} - {error_response.error}"
        })
```

### Error Rate Monitoring

Monitor error rates and alert on thresholds:

```python
async def monitor_error_rate():
    """Monitor error rates and alert if threshold exceeded"""
    error_count = await get_error_count_last_hour()
    total_requests = await get_total_requests_last_hour()
    error_rate = error_count / total_requests if total_requests > 0 else 0
    
    if error_rate > 0.05:  # 5% error rate threshold
        await session.call_tool("create_system_alert", {
            "alert_type": "WARNING",
            "message": f"High error rate: {error_rate:.2%}"
        })
```

## Support

For error handling support:
- Check error code documentation in API_REFERENCE.md
- Review logs for detailed error context
- Monitor error metrics in Grafana
- Contact support for persistent issues
