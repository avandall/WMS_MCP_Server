# Testing Guidelines

This document provides comprehensive guidelines for testing the WMS MCP Server, including unit tests, integration tests, and end-to-end tests.

## Table of Contents

- [Testing Philosophy](#testing-philosophy)
- [Test Structure](#test-structure)
- [Unit Testing](#unit-testing)
- [Integration Testing](#integration-testing)
- [End-to-End Testing](#end-to-end-testing)
- [Test Coverage](#test-coverage)
- [Test Data Management](#test-data-management)
- [Mocking and Fixtures](#mocking-and-fixtures)
- [Running Tests](#running-tests)
- [CI/CD Integration](#cicd-integration)
- [Best Practices](#best-practices)

## Testing Philosophy

### Principles

1. **Test Isolation**: Each test should be independent and not depend on other tests
2. **Fast Feedback**: Unit tests should run quickly (under 1 second per test)
3. **Clear Intent**: Test names should clearly describe what they test
4. **AAA Pattern**: Arrange, Act, Assert structure for clarity
5. **Test Behavior, Not Implementation**: Focus on what the code does, not how

### Testing Pyramid

```
        /\
       /E2E\      (10% - Critical user workflows)
      /------\
     /Integration\ (30% - Component interactions)
    /------------\
   /   Unit Tests  \ (60% - Individual functions)
  /----------------\
```

- **Unit Tests**: 60% - Test individual functions and classes
- **Integration Tests**: 30% - Test component interactions
- **E2E Tests**: 10% - Test critical user workflows

## Test Structure

### Directory Structure

```
tests/
├── unit/
│   ├── tools/
│   │   ├── test_inventory_tools.py
│   │   ├── test_transaction_tools.py
│   │   └── test_monitoring_tools.py
│   ├── clients/
│   │   ├── test_database_client.py
│   │   ├── test_redis_client.py
│   │   └── test_queue_client.py
│   └── utils/
│       ├── test_validators.py
│       └── test_helpers.py
├── integration/
│   ├── test_database_integration.py
│   ├── test_redis_integration.py
│   ├── test_queue_integration.py
│   └── test_tool_integration.py
├── e2e/
│   ├── test_order_fulfillment.py
│   ├── test_inbound_receiving.py
│   └── test_inventory_audit.py
├── fixtures/
│   ├── conftest.py
│   ├── database_fixtures.py
│   ├── redis_fixtures.py
│   └── test_data_fixtures.py
└── conftest.py
```

### Test File Naming

- Unit tests: `test_<module_name>.py`
- Integration tests: `test_<integration_name>.py`
- E2E tests: `test_<workflow_name>.py`

### Test Class Naming

```python
# Good: Descriptive class name
class TestCheckStockAvailability:
    pass

# Bad: Generic class name
class TestTool:
    pass
```

### Test Method Naming

```python
# Good: Descriptive method name
def test_valid_sku_code_returns_available_quantity():
    pass

def test_invalid_sku_code_returns_not_found_error():
    pass

# Bad: Generic method name
def test_tool():
    pass
```

## Unit Testing

### Writing Unit Tests

```python
import pytest
from app.tools.inventory.check_stock_availability import CheckStockAvailabilityTool
from app.models.tool_input import CheckStockAvailabilityInput

class TestCheckStockAvailability:
    """Unit tests for check_stock_availability tool."""
    
    @pytest.fixture
    def tool(self, mock_db_client):
        """Fixture for tool instance with mocked database."""
        return CheckStockAvailabilityTool(mock_db_client)
    
    @pytest.mark.asyncio
    async def test_valid_sku_code_returns_available_quantity(self, tool):
        """Test that valid SKU code returns available quantity."""
        # Arrange
        input_data = CheckStockAvailabilityInput(
            sku_code="SKU-1060-6GB",
            warehouse_id=1
        )
        tool.db_client.fetch.return_value = [
            {"sku_code": "SKU-1060-6GB", "available_quantity": 100}
        ]
        
        # Act
        result = await tool.execute(input_data)
        
        # Assert
        assert result.success is True
        assert result.data["available_quantity"] == 100
        tool.db_client.fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invalid_sku_code_returns_not_found_error(self, tool):
        """Test that invalid SKU code returns NOT_FOUND error."""
        # Arrange
        input_data = CheckStockAvailabilityInput(
            sku_code="INVALID-SKU",
            warehouse_id=1
        )
        tool.db_client.fetch.return_value = []
        
        # Act
        result = await tool.execute(input_data)
        
        # Assert
        assert result.success is False
        assert result.error_code == "NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_database_error_returns_database_error(self, tool):
        """Test that database error returns DATABASE_ERROR."""
        # Arrange
        input_data = CheckStockAvailabilityInput(
            sku_code="SKU-1060-6GB",
            warehouse_id=1
        )
        tool.db_client.fetch.side_effect = Exception("Connection failed")
        
        # Act
        result = await tool.execute(input_data)
        
        # Assert
        assert result.success is False
        assert result.error_code == "DATABASE_ERROR"
```

### Testing Validation

```python
import pytest
from pydantic import ValidationError

def test_sku_code_validation():
    """Test SKU code validation."""
    # Valid SKU code
    input_data = CheckStockAvailabilityInput(
        sku_code="SKU-1060-6GB",
        warehouse_id=1
    )
    assert input_data.sku_code == "SKU-1060-6GB"
    
    # Invalid SKU code (empty)
    with pytest.raises(ValidationError):
        CheckStockAvailabilityInput(
            sku_code="",
            warehouse_id=1
        )
    
    # Invalid SKU code (wrong format)
    with pytest.raises(ValidationError):
        CheckStockAvailabilityInput(
            sku_code="INVALID",
            warehouse_id=1
        )
```

### Testing Error Handling

```python
@pytest.mark.asyncio
async def test_lock_acquisition_failure_handling(self, tool):
    """Test handling of lock acquisition failure."""
    # Arrange
    input_data = UpdateInventoryQuantityInput(
        sku_code="SKU-1060-6GB",
        location_code="ZONE-A-ROW-01-SHELF-01",
        action="INCREASE",
        quantity=10
    )
    tool.redis_client.acquire_lock.return_value = False
    
    # Act
    result = await tool.execute(input_data)
    
    # Assert
    assert result.success is False
    assert result.error_code == "LOCK_ACQUISITION_FAILED"
```

## Integration Testing

### Database Integration Tests

```python
import pytest
import asyncpg
from app.clients.database import DatabaseClient

@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database client."""
    
    @pytest.fixture
    async def db_client(self):
        """Fixture for real database connection."""
        client = DatabaseClient(DATABASE_URL)
        await client.initialize()
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_connect_to_database(self, db_client):
        """Test connecting to database."""
        # Act
        result = await db_client.fetch("SELECT 1")
        
        # Assert
        assert len(result) == 1
        assert result[0]["?column?"] == 1
    
    @pytest.mark.asyncio
    async def test_insert_and_query(self, db_client):
        """Test inserting and querying data."""
        # Arrange
        sku_code = "TEST-SKU-001"
        
        # Act
        await db_client.execute(
            "INSERT INTO inventory (sku_code, quantity) VALUES ($1, $2)",
            sku_code, 100
        )
        result = await db_client.fetch(
            "SELECT quantity FROM inventory WHERE sku_code = $1",
            sku_code
        )
        
        # Assert
        assert result[0]["quantity"] == 100
        
        # Cleanup
        await db_client.execute(
            "DELETE FROM inventory WHERE sku_code = $1",
            sku_code
        )
```

### Redis Integration Tests

```python
import pytest
import aioredis
from app.clients.redis import RedisClient

@pytest.mark.integration
class TestRedisIntegration:
    """Integration tests for Redis client."""
    
    @pytest.fixture
    async def redis_client(self):
        """Fixture for real Redis connection."""
        client = RedisClient(REDIS_URL)
        await client.initialize()
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, redis_client):
        """Test setting and getting values."""
        # Arrange
        key = "test_key"
        value = "test_value"
        
        # Act
        await redis_client.set(key, value)
        result = await redis_client.get(key)
        
        # Assert
        assert result == value
        
        # Cleanup
        await redis_client.delete(key)
    
    @pytest.mark.asyncio
    async def test_lock_acquisition(self, redis_client):
        """Test distributed lock acquisition."""
        # Arrange
        lock_key = "lock:test"
        
        # Act
        acquired = await redis_client.acquire_lock(lock_key, ttl=10)
        
        # Assert
        assert acquired is True
        
        # Try to acquire again (should fail)
        acquired_again = await redis_client.acquire_lock(lock_key, ttl=10)
        assert acquired_again is False
        
        # Cleanup
        await redis_client.release_lock(lock_key)
```

### Message Queue Integration Tests

```python
import pytest
import aio_pika
from app.clients.queue import QueueClient

@pytest.mark.integration
class TestQueueIntegration:
    """Integration tests for message queue client."""
    
    @pytest.fixture
    async def queue_client(self):
        """Fixture for real queue connection."""
        client = QueueClient(RABBITMQ_URL)
        await client.initialize()
        yield client
        await client.close()
    
    @pytest.mark.asyncio
    async def test_publish_and_consume(self, queue_client):
        """Test publishing and consuming messages."""
        # Arrange
        queue_name = "test_queue"
        message = {"test": "data"}
        
        # Act
        await queue_client.publish(queue_name, message)
        consumed = await queue_client.consume(queue_name)
        
        # Assert
        assert consumed == message
        
        # Cleanup
        await queue_client.delete_queue(queue_name)
```

## End-to-End Testing

### Order Fulfillment Workflow

```python
import pytest
from mcp import ClientSession, StdioServerParameters

@pytest.mark.e2e
class TestOrderFulfillmentWorkflow:
    """E2E tests for order fulfillment workflow."""
    
    @pytest.fixture
    async def session(self):
        """Fixture for MCP client session."""
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "app.server"],
            env={"WMS_API_KEY": "test-api-key"}
        )
        async with ClientSession(server_params) as session:
            await session.initialize()
            yield session
    
    @pytest.mark.asyncio
    async def test_complete_order_fulfillment(self, session):
        """Test complete order fulfillment workflow."""
        # Step 1: Get order details
        order_result = await session.call_tool("get_order_status_details", {
            "order_id": "ORDER-2024-00890"
        })
        assert order_result.success is True
        assert order_result.data["order_info"]["status"] == "CONFIRMED"
        
        # Step 2: Generate picking route
        route_result = await session.call_tool("generate_picking_route", {
            "order_id": "ORDER-2024-00890"
        })
        assert route_result.success is True
        assert len(route_result.data["route"]) > 0
        
        # Step 3: Assign picking task
        assign_result = await session.call_tool("assign_picking_task", {
            "task_id": "TASK-ORDER-2024-00890",
            "user_id": "USER-0056"
        })
        assert assign_result.success is True
        
        # Step 4: Suggest packing box
        box_result = await session.call_tool("suggest_packing_box", {
            "order_id": "ORDER-2024-00890"
        })
        assert box_result.success is True
        assert "recommended_box" in box_result.data
        
        # Step 5: Create shipping label
        label_result = await session.call_tool("create_shipping_label", {
            "order_id": "ORDER-2024-00890",
            "carrier_id": "DHL"
        })
        assert label_result.success is True
        assert "tracking_number" in label_result.data
```

### Inbound Receiving Workflow

```python
@pytest.mark.e2e
class TestInboundReceivingWorkflow:
    """E2E tests for inbound receiving workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_inbound_receiving(self, session):
        """Test complete inbound receiving workflow."""
        # Step 1: Verify PO
        verify_result = await session.call_tool("verify_incoming_po", {
            "po_number": "PO-2024-00123"
        })
        assert verify_result.success is True
        
        # Step 2: Get ABC classification
        abc_result = await session.call_tool("abc_analysis_report", {
            "sku_code": "SKU-1060-6GB"
        })
        assert abc_result.success is True
        
        # Step 3: Get slotting recommendation
        slot_result = await session.call_tool("smart_slotting_optimizer", {
            "sku_code": "SKU-1060-6GB",
            "quantity": 50
        })
        assert slot_result.success is True
        
        # Step 4: Update inventory
        location = slot_result.data["recommended_locations"][0]["location_code"]
        update_result = await session.call_tool("update_inventory_quantity", {
            "sku_code": "SKU-1060-6GB",
            "location_code": location,
            "action": "INCREASE",
            "quantity": 50
        })
        assert update_result.success is True
```

## Test Coverage

### Coverage Goals

- **Overall Coverage**: Minimum 80%
- **Critical Path Coverage**: Minimum 95%
- **Tool Coverage**: Minimum 90%

### Running Coverage Reports

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# Generate terminal report
pytest --cov=app --cov-report=term-missing

# Generate XML report (for CI/CD)
pytest --cov=app --cov-report=xml

# View HTML report
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
```

### Coverage Configuration

Create `.coveragerc`:

```ini
[run]
source = app
omit = 
    */tests/*
    */venv/*
    */__pycache__/*
    */migrations/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if TYPE_CHECKING:
    @abstractmethod
precision = 2
```

### Interpreting Coverage

- **Line Coverage**: Percentage of executable lines executed
- **Branch Coverage**: Percentage of conditional branches taken
- **Function Coverage**: Percentage of functions called

## Test Data Management

### Fixtures

```python
# tests/fixtures/conftest.py
import pytest
from app.clients.database import DatabaseClient
from app.clients.redis import RedisClient

@pytest.fixture
async def db_client():
    """Fixture for database client."""
    client = DatabaseClient(DATABASE_URL)
    await client.initialize()
    yield client
    await client.close()

@pytest.fixture
async def redis_client():
    """Fixture for Redis client."""
    client = RedisClient(REDIS_URL)
    await client.initialize()
    yield client
    await client.close()

@pytest.fixture
def sample_sku():
    """Fixture for sample SKU data."""
    return {
        "sku_code": "SKU-1060-6GB",
        "description": "NVIDIA RTX 1060 6GB",
        "quantity": 100,
        "location_code": "ZONE-A-ROW-01-SHELF-01"
    }

@pytest.fixture
def sample_order():
    """Fixture for sample order data."""
    return {
        "order_id": "ORDER-2024-00890",
        "customer_id": "CUST-001",
        "items": [
            {"sku_code": "SKU-1060-6GB", "quantity": 2}
        ]
    }
```

### Test Data Factories

```python
# tests/fixtures/factories.py
from faker import Faker

fake = Faker()

class SKUFactory:
    """Factory for creating SKU data."""
    
    @staticmethod
    def create(**kwargs):
        """Create SKU data with defaults."""
        defaults = {
            "sku_code": f"SKU-{fake.random_int(1000, 9999)}-{fake.random_element(['4GB', '6GB', '8GB'])}",
            "description": fake.sentence(),
            "quantity": fake.random_int(10, 1000),
            "location_code": f"ZONE-{fake.random_element(['A', 'B', 'C'])}-ROW-{fake.random_int(1, 10)}-SHELF-{fake.random_int(1, 5)}"
        }
        defaults.update(kwargs)
        return defaults

class OrderFactory:
    """Factory for creating order data."""
    
    @staticmethod
    def create(**kwargs):
        """Create order data with defaults."""
        defaults = {
            "order_id": f"ORDER-{fake.year()}-{fake.random_int(10000, 99999)}",
            "customer_id": f"CUST-{fake.random_int(1, 1000)}",
            "status": "CONFIRMED",
            "items": [
                {
                    "sku_code": SKUFactory.create()["sku_code"],
                    "quantity": fake.random_int(1, 10)
                }
            ]
        }
        defaults.update(kwargs)
        return defaults
```

### Database Seeding

```python
# tests/fixtures/database_fixtures.py
import pytest
from app.clients.database import DatabaseClient

@pytest.fixture
async def seeded_database(db_client):
    """Fixture for database with test data."""
    # Seed test data
    await db_client.execute("""
        INSERT INTO inventory (sku_code, quantity, location_code)
        VALUES ('SKU-TEST-001', 100, 'ZONE-A-ROW-01-SHELF-01')
    """)
    
    yield db_client
    
    # Cleanup
    await db_client.execute("DELETE FROM inventory WHERE sku_code LIKE 'SKU-TEST-%'")
```

## Mocking and Fixtures

### Mocking Database

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_db_client():
    """Fixture for mocked database client."""
    client = MagicMock()
    client.fetch = AsyncMock()
    client.execute = AsyncMock()
    client.fetchrow = AsyncMock()
    return client
```

### Mocking Redis

```python
@pytest.fixture
def mock_redis_client():
    """Fixture for mocked Redis client."""
    client = MagicMock()
    client.get = AsyncMock()
    client.set = AsyncMock()
    client.delete = AsyncMock()
    client.acquire_lock = AsyncMock(return_value=True)
    client.release_lock = AsyncMock()
    return client
```

### Mocking External APIs

```python
@pytest.fixture
def mock_shipping_client():
    """Fixture for mocked shipping client."""
    client = MagicMock()
    client.create_label = AsyncMock(return_value={
        "tracking_number": "1234567890",
        "label_url": "https://example.com/label.pdf"
    })
    return client
```

### Using Mocks in Tests

```python
@pytest.mark.asyncio
async def test_with_mocked_dependencies(self, mock_db_client, mock_redis_client):
    """Test with mocked dependencies."""
    tool = UpdateInventoryQuantityTool(
        db_client=mock_db_client,
        redis_client=mock_redis_client
    )
    
    input_data = UpdateInventoryQuantityInput(
        sku_code="SKU-1060-6GB",
        location_code="ZONE-A-ROW-01-SHELF-01",
        action="INCREASE",
        quantity=10
    )
    
    result = await tool.execute(input_data)
    
    assert result.success is True
    mock_db_client.execute.assert_called_once()
    mock_redis_client.acquire_lock.assert_called_once()
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_inventory_tools.py

# Run specific test class
pytest tests/unit/test_inventory_tools.py::TestCheckStockAvailability

# Run specific test
pytest tests/unit/test_inventory_tools.py::TestCheckStockAvailability::test_valid_sku_code

# Run tests matching pattern
pytest -k "check_stock"

# Run tests with markers
pytest -m unit
pytest -m integration
pytest -m e2e
```

### Running with Coverage

```bash
# Run with coverage
pytest --cov=app --cov-report=html

# Run with coverage for specific module
pytest --cov=app.tools.inventory --cov-report=html

# Run with coverage and fail if below threshold
pytest --cov=app --cov-fail-under=80
```

### Running in Parallel

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU count)
pytest -n auto

# Run with specific number of workers
pytest -n 4
```

### Running with Debugging

```bash
# Stop on first failure
pytest -x

# Stop on first failure and enter debugger
pytest -x --pdb

# Enter debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l
```

## CI/CD Integration

### GitHub Actions Configuration

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: wms_user
          POSTGRES_PASSWORD: wms_password
          POSTGRES_DB: wms_test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      
      - name: Run migrations
        env:
          DATABASE_URL: postgresql://wms_user:wms_password@localhost:5432/wms_test_db
        run: |
          python -m alembic upgrade head
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://wms_user:wms_password@localhost:5432/wms_test_db
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest --cov=app --cov-report=xml --cov-report=term
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
        language_version: python3.13
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
  
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

## Best Practices

### 1. Write Descriptive Test Names

```python
# Good
def test_valid_sku_code_returns_available_quantity():
    pass

# Bad
def test_tool():
    pass
```

### 2. Use AAA Pattern

```python
def test_update_inventory():
    # Arrange
    tool = UpdateInventoryQuantityTool()
    input_data = UpdateInventoryQuantityInput(...)
    
    # Act
    result = await tool.execute(input_data)
    
    # Assert
    assert result.success is True
```

### 3. Test One Thing per Test

```python
# Good: Single assertion
def test_valid_sku_code():
    result = tool.execute(input_data)
    assert result.success is True

# Bad: Multiple assertions
def test_tool():
    result = tool.execute(input_data)
    assert result.success is True
    assert result.data["quantity"] == 100
    assert result.data["location"] == "ZONE-A"
```

### 4. Use Fixtures for Reusable Setup

```python
# Good: Use fixtures
@pytest.fixture
def tool():
    return CheckStockAvailabilityTool()

def test_tool(tool):
    result = tool.execute(input_data)
    assert result.success is True

# Bad: Duplicate setup
def test_tool_1():
    tool = CheckStockAvailabilityTool()
    result = tool.execute(input_data)
    assert result.success is True

def test_tool_2():
    tool = CheckStockAvailabilityTool()
    result = tool.execute(input_data)
    assert result.success is True
```

### 5. Mock External Dependencies

```python
# Good: Mock external API
@pytest.mark.asyncio
async def test_shipping_label(mock_shipping_client):
    tool = CreateShippingLabelTool(shipping_client=mock_shipping_client)
    result = await tool.execute(input_data)
    assert result.success is True

# Bad: Call real API
@pytest.mark.asyncio
async def test_shipping_label():
    tool = CreateShippingLabelTool()
    result = await tool.execute(input_data)
    assert result.success is True  # May fail due to API issues
```

### 6. Clean Up Test Data

```python
# Good: Cleanup in fixture
@pytest.fixture
async def test_data(db_client):
    await db_client.execute("INSERT INTO ...")
    yield db_client
    await db_client.execute("DELETE FROM ...")

# Bad: No cleanup
@pytest.fixture
async def test_data(db_client):
    await db_client.execute("INSERT INTO ...")
    yield db_client
    # Data remains in database
```

### 7. Use Markers for Test Categories

```python
# Good: Use markers
@pytest.mark.unit
def test_function():
    pass

@pytest.mark.integration
def test_integration():
    pass

# Bad: No markers
def test_function():
    pass
```

### 8. Test Error Conditions

```python
# Good: Test error conditions
def test_invalid_input_returns_validation_error():
    result = tool.execute(invalid_input)
    assert result.success is False
    assert result.error_code == "VALIDATION_ERROR"

# Bad: Only test success cases
def test_valid_input():
    result = tool.execute(valid_input)
    assert result.success is True
```

### 9. Keep Tests Independent

```python
# Good: Independent tests
def test_1():
    result = tool.execute(input_1)
    assert result.success is True

def test_2():
    result = tool.execute(input_2)
    assert result.success is True

# Bad: Dependent tests
def test_1():
    global state
    state = tool.execute(input_1)

def test_2():
    result = tool.execute(input_2, state)  # Depends on test_1
```

### 10. Use Parameterized Tests

```python
# Good: Parameterized
@pytest.mark.parametrize("sku_code,expected", [
    ("SKU-1060-6GB", True),
    ("SKU-RTX-3080", True),
    ("INVALID-SKU", False),
])
def test_sku_code_validation(sku_code, expected):
    result = tool.validate(sku_code)
    assert result == expected

# Bad: Duplicate tests
def test_valid_sku_1():
    result = tool.validate("SKU-1060-6GB")
    assert result is True

def test_valid_sku_2():
    result = tool.validate("SKU-RTX-3080")
    assert result is True
```

## Troubleshooting

### Common Issues

#### Tests Fail in CI but Pass Locally

**Causes**:
- Different environment variables
- Different database state
- Timing issues

**Solutions**:
- Ensure consistent test data setup
- Use fixtures for environment setup
- Add delays for async operations

#### Flaky Tests

**Causes**:
- Race conditions
- External dependencies
- Timing issues

**Solutions**:
- Mock external dependencies
- Use proper async/await
- Add retries for transient failures

#### Slow Tests

**Causes**:
- Too many integration tests
- Database operations
- Network calls

**Solutions**:
- Use mocks for external dependencies
- Use test database with minimal data
- Run tests in parallel

#### Import Errors in Tests

**Causes**:
- Wrong PYTHONPATH
- Missing dependencies
- Wrong test structure

**Solutions**:
- Ensure virtual environment is activated
- Install all dependencies
- Check test directory structure

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [pytest-xdist Documentation](https://pytest-xdist.readthedocs.io/)
