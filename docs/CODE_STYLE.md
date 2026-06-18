# Code Style Guide

This document defines the coding standards and style guidelines for the WMS MCP Server project.

## Table of Contents

- [Python Style Guide](#python-style-guide)
- [Naming Conventions](#naming-conventions)
- [Code Organization](#code-organization)
- [Type Hints](#type-hints)
- [Docstrings](#docstrings)
- [Error Handling](#error-handling)
- [Logging](#logging)
- [Async/Await Patterns](#asyncawait-patterns)
- [Testing Style](#testing-style)
- [Git Commit Style](#git-commit-style)

## Python Style Guide

We follow PEP 8 with some modifications enforced by Black.

### Code Formatting

We use **Black** for code formatting with the following configuration:

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py313']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

### Running Black

```bash
# Format code
black app/ tests/

# Check formatting without modifying
black --check app/ tests/

# Format specific file
black app/tools/inventory/check_stock_availability.py
```

### Line Length

- Maximum line length: **100 characters**
- Black will automatically wrap lines exceeding this limit

### Imports

**Good**:
```python
# Standard library imports
import asyncio
import logging
from typing import Optional, List, Dict

# Third-party imports
import asyncpg
import aioredis
from pydantic import BaseModel, Field

# Local imports
from app.tools.base import BaseTool
from app.clients.database import DatabaseClient
```

**Bad**:
```python
# Mixed imports
import asyncio
from app.tools.base import BaseTool
import asyncpg
from typing import Optional
```

### Whitespace

- Use 4 spaces for indentation (no tabs)
- Blank lines between class methods (1 line)
- Blank lines between top-level functions (2 lines)
- No trailing whitespace

## Naming Conventions

### Variables and Functions

Use **snake_case** for variables and functions:

```python
# Good
sku_code = "SKU-1060-6GB"
available_quantity = 100
def check_stock_availability():
    pass

# Bad
skuCode = "SKU-1060-6GB"
availableQuantity = 100
def checkStockAvailability():
    pass
```

### Classes

Use **PascalCase** for classes:

```python
# Good
class CheckStockAvailabilityTool:
    pass

class DatabaseClient:
    pass

# Bad
class check_stock_availability_tool:
    pass

class database_client:
    pass
```

### Constants

Use **UPPER_SNAKE_CASE** for constants:

```python
# Good
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
DATABASE_POOL_SIZE = 20

# Bad
max_retries = 3
default_timeout = 30
```

### Private Members

Use **single underscore prefix** for protected members:

```python
# Good
class Tool:
    def __init__(self):
        self._db_client = None
        self._logger = None

# Bad
class Tool:
    def __init__(self):
        self.db_client = None
        self.logger = None
```

### Dunder Methods

Use **double underscore** for special methods:

```python
# Good
class Tool:
    def __init__(self):
        pass
    
    def __str__(self):
        return "Tool"

# Bad
class Tool:
    def init(self):
        pass
    
    def str(self):
        return "Tool"
```

## Code Organization

### File Structure

```python
# 1. Module docstring
"""Module description."""

# 2. Imports (standard, third-party, local)
import asyncio
from typing import Optional

import asyncpg
from pydantic import BaseModel

from app.tools.base import BaseTool

# 3. Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# 4. Classes
class ToolInput(BaseModel):
    """Input schema."""

class Tool(BaseTool):
    """Tool implementation."""

# 5. Functions
async def helper_function():
    """Helper function."""
```

### Class Organization

```python
class CheckStockAvailabilityTool(BaseTool):
    """Tool for checking stock availability."""
    
    # 1. Class attributes
    name = "check_stock_availability"
    description = "Check stock availability for a SKU"
    
    # 2. __init__ method
    def __init__(self, db_client: DatabaseClient):
        """Initialize tool."""
        super().__init__()
        self._db_client = db_client
    
    # 3. Public methods
    async def execute(self, input_data: ToolInput) -> dict:
        """Execute the tool."""
        pass
    
    # 4. Protected methods
    async def _validate_input(self, input_data: ToolInput) -> bool:
        """Validate input."""
        pass
    
    # 5. Private methods
    async def __internal_method(self):
        """Internal method."""
        pass
```

## Type Hints

We use **type hints** for all function signatures and class attributes.

### Function Type Hints

```python
# Good
from typing import Optional, List, Dict

async def check_stock_availability(
    sku_code: str,
    warehouse_id: int,
    timeout: Optional[int] = None
) -> Dict[str, any]:
    """Check stock availability."""
    pass

# Bad
async def check_stock_availability(sku_code, warehouse_id, timeout=None):
    """Check stock availability."""
    pass
```

### Class Attribute Type Hints

```python
# Good
class DatabaseClient:
    """Database client."""
    
    def __init__(self, url: str):
        """Initialize client."""
        self._url: str = url
        self._pool: Optional[asyncpg.Pool] = None
        self._connection_count: int = 0

# Bad
class DatabaseClient:
    """Database client."""
    
    def __init__(self, url):
        """Initialize client."""
        self._url = url
        self._pool = None
        self._connection_count = 0
```

### Complex Type Hints

```python
# Good
from typing import List, Dict, Optional, Union

def process_items(
    items: List[Dict[str, Union[str, int]]],
    filter_func: Optional[callable] = None
) -> List[Dict[str, any]]:
    """Process items."""
    pass

# Bad
def process_items(items, filter_func=None):
    """Process items."""
    pass
```

## Docstrings

We use **Google-style docstrings** for all public functions and classes.

### Function Docstrings

```python
def check_stock_availability(
    sku_code: str,
    warehouse_id: int
) -> Dict[str, any]:
    """Check stock availability for a SKU.
    
    Args:
        sku_code: The SKU code to check
        warehouse_id: The warehouse ID to check
        
    Returns:
        Dictionary containing:
            - available_quantity: Available quantity
            - physical_quantity: Physical quantity
            - reserved_quantity: Reserved quantity
            
    Raises:
        ValueError: If sku_code is empty
        DatabaseError: If database query fails
        
    Example:
        >>> check_stock_availability("SKU-1060-6GB", 1)
        {
            "available_quantity": 100,
            "physical_quantity": 120,
            "reserved_quantity": 20
        }
    """
    pass
```

### Class Docstrings

```python
class CheckStockAvailabilityTool(BaseTool):
    """Tool for checking stock availability.
    
    This tool queries the database to retrieve stock information
    for a given SKU code and warehouse ID. It returns both
    physical and available quantities.
    
    Attributes:
        name: Tool name
        description: Tool description
        _db_client: Database client instance
        
    Example:
        >>> tool = CheckStockAvailabilityTool(db_client)
        >>> result = await tool.execute(input_data)
    """
    
    name = "check_stock_availability"
    description = "Check stock availability for a SKU"
```

### Module Docstrings

```python
"""Inventory tools module.

This module contains tools for inventory management including:
- check_stock_availability: Check stock levels
- inspect_shelf_capacity: Check shelf capacity
- abc_analysis_report: Get ABC classification
- smart_slotting_optimizer: Optimize slotting

Example:
    >>> from app.tools.inventory import check_stock_availability
    >>> tool = check_stock_availability.CheckStockAvailabilityTool()
"""
```

## Error Handling

### Exception Handling

```python
# Good: Specific exception handling
async def execute_tool(self, input_data: ToolInput) -> dict:
    """Execute the tool."""
    try:
        result = await self._db_client.fetch(query)
    except DatabaseConnectionError as e:
        logger.error(f"Database connection failed: {e}")
        return {"success": False, "error_code": "DATABASE_ERROR"}
    except DatabaseQueryError as e:
        logger.warning(f"Query failed: {e}")
        return {"success": False, "error_code": "DATABASE_ERROR"}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"success": False, "error_code": "INTERNAL_ERROR"}

# Bad: Generic exception handling
async def execute_tool(self, input_data: ToolInput) -> dict:
    """Execute the tool."""
    try:
        result = await self._db_client.fetch(query)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
```

### Custom Exceptions

```python
# Good: Custom exceptions
class ToolError(Exception):
    """Base exception for tool errors."""
    pass

class ValidationError(ToolError):
    """Validation error."""
    pass

class DatabaseError(ToolError):
    """Database error."""
    pass

# Usage
if not sku_code:
    raise ValidationError("SKU code is required")
```

### Error Messages

```python
# Good: Descriptive error messages
if not sku_code:
    raise ValueError("SKU code cannot be empty")

if quantity < 0:
    raise ValueError(f"Quantity must be non-negative, got {quantity}")

# Bad: Generic error messages
if not sku_code:
    raise ValueError("Invalid input")

if quantity < 0:
    raise ValueError("Error")
```

## Logging

### Logger Setup

```python
import logging

logger = logging.getLogger(__name__)

class Tool:
    """Tool implementation."""
    
    def __init__(self):
        """Initialize tool."""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
```

### Log Levels

```python
# DEBUG: Detailed diagnostic information
logger.debug(f"Executing query: {query}")

# INFO: General information about execution
logger.info(f"Processing order {order_id}")

# WARNING: Warning about potential issues
logger.warning(f"Low stock for SKU {sku_code}: {quantity}")

# ERROR: Error occurred but execution continued
logger.error(f"Failed to update inventory: {error}")

# CRITICAL: Critical error requiring immediate attention
logger.critical(f"Database connection lost: {error}")
```

### Log Formatting

```python
# Good: Structured log messages
logger.info(
    "Processing order",
    extra={
        "order_id": order_id,
        "customer_id": customer_id,
        "item_count": len(items)
    }
)

# Bad: Unstructured log messages
logger.info(f"Processing order {order_id} for customer {customer_id} with {len(items)} items")
```

### Sensitive Data

```python
# Good: Mask sensitive data
logger.info(f"Processing order {order_id}")
logger.debug(f"API key: {mask_api_key(api_key)}")

# Bad: Log sensitive data
logger.info(f"Processing order {order_id} with API key {api_key}")
```

## Async/Await Patterns

### Async Function Definition

```python
# Good: Use async for I/O operations
async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Bad: Use async for CPU-bound operations
async def calculate_fibonacci(n: int) -> int:
    """Calculate Fibonacci number."""
    # This should be a regular function
    pass
```

### Await Usage

```python
# Good: Proper await usage
async def process_order(self, order_id: str) -> dict:
    """Process order."""
    order = await self._get_order(order_id)
    items = await self._get_order_items(order_id)
    return {"order": order, "items": items}

# Bad: Missing await
async def process_order(self, order_id: str) -> dict:
    """Process order."""
    order = self._get_order(order_id)  # Missing await
    items = self._get_order_items(order_id)  # Missing await
    return {"order": order, "items": items}
```

### Async Context Managers

```python
# Good: Use async context managers
async def execute_query(self, query: str) -> list:
    """Execute database query."""
    async with self._pool.acquire() as conn:
        return await conn.fetch(query)

# Bad: Manual resource management
async def execute_query(self, query: str) -> list:
    """Execute database query."""
    conn = await self._pool.acquire()
    try:
        return await conn.fetch(query)
    finally:
        await self._pool.release(conn)
```

### Concurrent Execution

```python
# Good: Use asyncio.gather for concurrent operations
async def fetch_multiple_skus(self, sku_codes: List[str]) -> List[dict]:
    """Fetch multiple SKUs concurrently."""
    tasks = [self._fetch_sku(sku) for sku in sku_codes]
    return await asyncio.gather(*tasks)

# Bad: Sequential execution
async def fetch_multiple_skus(self, sku_codes: List[str]) -> List[dict]:
    """Fetch multiple SKUs."""
    results = []
    for sku in sku_codes:
        result = await self._fetch_sku(sku)
        results.append(result)
    return results
```

## Testing Style

### Test Structure

```python
# Good: AAA pattern (Arrange, Act, Assert)
class TestCheckStockAvailability:
    """Tests for check_stock_availability tool."""
    
    @pytest.mark.asyncio
    async def test_valid_sku_code(self, tool):
        """Test with valid SKU code."""
        # Arrange
        input_data = ToolInput(sku_code="SKU-1060-6GB", warehouse_id=1)
        
        # Act
        result = await tool.execute(input_data)
        
        # Assert
        assert result.success is True
        assert result.data["available_quantity"] > 0

# Bad: No clear structure
class TestCheckStockAvailability:
    """Tests for check_stock_availability tool."""
    
    @pytest.mark.asyncio
    async def test_valid_sku_code(self, tool):
        result = await tool.execute(ToolInput(sku_code="SKU-1060-6GB", warehouse_id=1))
        assert result.success is True
```

### Test Naming

```python
# Good: Descriptive test names
def test_valid_sku_code_returns_available_quantity():
    pass

def test_invalid_sku_code_returns_not_found_error():
    pass

def test_database_connection_failure_returns_database_error():
    pass

# Bad: Generic test names
def test_tool():
    pass

def test_error():
    pass
```

### Test Organization

```python
# Good: Group related tests
class TestCheckStockAvailability:
    """Tests for check_stock_availability tool."""
    
    @pytest.mark.asyncio
    async def test_valid_sku_code(self):
        """Test with valid SKU code."""
        pass
    
    @pytest.mark.asyncio
    async def test_invalid_sku_code(self):
        """Test with invalid SKU code."""
        pass
    
    @pytest.mark.asyncio
    async def test_database_error(self):
        """Test database error handling."""
        pass

# Bad: No organization
def test_1():
    pass

def test_2():
    pass

def test_3():
    pass
```

## Git Commit Style

We follow **Conventional Commits** specification.

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

### Examples

```
feat(inventory): add smart slotting optimizer

Implements ABC-based slotting optimization algorithm
to suggest optimal storage locations based on
turnover rate and item value.

- Add abc_analysis_report tool
- Add smart_slotting_optimizer tool
- Update documentation

Closes #123
```

```
fix(auth): resolve API key validation issue

Fixes bug where API keys with special characters
were not being validated correctly.

Fixes #456
```

```
docs(api): update API reference documentation

Updated API_REFERENCE.md with detailed endpoint
documentation for all 19 tools including
request/response examples.
```

### Subject Line

- Use present tense ("add" not "added")
- Use imperative mood ("add" not "adds")
- Capitalize first letter
- No period at end
- Limit to 50 characters

### Body

- Wrap at 72 characters
- Explain what and why, not how
- Use bullet points for multiple items

### Footer

- Reference issue numbers
- Reference PR numbers
- Add breaking change notices

## Code Quality Tools

### Black (Code Formatter)

```bash
# Format code
black app/ tests/

# Check formatting
black --check app/ tests/
```

### Flake8 (Linter)

```bash
# Run flake8
flake8 app/ tests/

# Configuration in .flake8
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv
```

### mypy (Type Checker)

```bash
# Run mypy
mypy app/

# Configuration in mypy.ini
[mypy]
python_version = 3.13
warn_return_any = True
warn_unused_configs = True
```

### isort (Import Sorter)

```bash
# Sort imports
isort app/ tests/

# Configuration in pyproject.toml
[tool.isort]
profile = "black"
line_length = 100
```

## Best Practices

### 1. Keep Functions Small

```python
# Good: Small, focused function
def calculate_abc_class(turnover_rate: float, value: float) -> str:
    """Calculate ABC class based on turnover and value."""
    if turnover_rate > 1000 and value > 10000:
        return "A"
    elif turnover_rate > 100 and value > 1000:
        return "B"
    else:
        return "C"

# Bad: Large, complex function
def process_inventory_data(data: dict) -> dict:
    """Process inventory data."""
    # 100 lines of code
    pass
```

### 2. Use Descriptive Names

```python
# Good: Descriptive names
def calculate_available_quantity(
    physical_quantity: int,
    reserved_quantity: int
) -> int:
    """Calculate available quantity."""
    return physical_quantity - reserved_quantity

# Bad: Generic names
def calc(q1: int, q2: int) -> int:
    """Calculate."""
    return q1 - q2
```

### 3. Avoid Magic Numbers

```python
# Good: Use constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

for attempt in range(MAX_RETRIES):
    result = await execute_with_timeout(DEFAULT_TIMEOUT)

# Bad: Magic numbers
for attempt in range(3):
    result = await execute_with_timeout(30)
```

### 4. Use List Comprehensions

```python
# Good: List comprehension
sku_codes = [item["sku_code"] for item in items if item["available"]]

# Bad: For loop
sku_codes = []
for item in items:
    if item["available"]:
        sku_codes.append(item["sku_code"])
```

### 5. Use Context Managers

```python
# Good: Context manager
async with database.acquire() as conn:
    result = await conn.fetch(query)

# Bad: Manual resource management
conn = await database.acquire()
try:
    result = await conn.fetch(query)
finally:
    await database.release(conn)
```

### 6. Handle Edge Cases

```python
# Good: Handle edge cases
def divide(a: int, b: int) -> float:
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# Bad: No edge case handling
def divide(a: int, b: int) -> float:
    """Divide two numbers."""
    return a / b
```

### 7. Use Type Hints

```python
# Good: Type hints
def process_items(items: List[Dict[str, any]]) -> List[str]:
    """Process items and return SKU codes."""
    return [item["sku_code"] for item in items]

# Bad: No type hints
def process_items(items):
    """Process items and return SKU codes."""
    return [item["sku_code"] for item in items]
```

### 8. Document Public APIs

```python
# Good: Documented public API
class CheckStockAvailabilityTool(BaseTool):
    """Tool for checking stock availability.
    
    This tool queries the database to retrieve stock information
    for a given SKU code and warehouse ID.
    
    Args:
        db_client: Database client instance
        
    Example:
        >>> tool = CheckStockAvailabilityTool(db_client)
        >>> result = await tool.execute(input_data)
    """
    pass

# Bad: Undocumented public API
class CheckStockAvailabilityTool(BaseTool):
    pass
```

## Resources

- [PEP 8 Style Guide](https://pep8.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Type Hints Documentation](https://docs.python.org/3/library/typing.html)
- [Conventional Commits](https://www.conventionalcommits.org/)
