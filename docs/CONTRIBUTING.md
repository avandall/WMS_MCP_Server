# Contributing to WMS MCP Server

Thank you for your interest in contributing to the WMS MCP Server! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and constructive in all interactions.

### Standards

- Use welcoming and inclusive language
- Be respectful of different viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Reporting Issues

If you witness or experience any unacceptable behavior, please contact the project maintainers privately.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.13 or higher
- Docker and Docker Compose
- Git
- A GitHub account

### Initial Setup

1. **Fork the Repository**

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/WMS_MCP_Server.git
cd WMS_MCP_Server
```

2. **Set Up Development Environment**

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Start development services
docker-compose up -d postgres redis rabbitmq
```

3. **Run Initial Setup**

```bash
# Run database migrations
python -m alembic upgrade head

# Run tests to verify setup
pytest
```

## Development Workflow

### Branch Strategy

We use a GitFlow-inspired branching strategy:

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Feature branches
- `bugfix/*`: Bug fix branches
- `hotfix/*`: Urgent production fixes

### Creating a Feature Branch

```bash
# Ensure your develop branch is up to date
git checkout develop
git pull origin develop

# Create a new feature branch
git checkout -b feature/your-feature-name
```

### Making Changes

1. **Write Code**
   - Follow coding standards (see [Coding Standards](#coding-standards))
   - Write tests for your changes
   - Update documentation as needed

2. **Commit Changes**

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new tool for inventory optimization"
```

3. **Commit Message Format**

We follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

**Examples:**
```
feat(inventory): add smart slotting optimizer

Implements ABC-based slotting optimization algorithm
to suggest optimal storage locations based on
turnover rate and item value.

Closes #123
```

```
fix(auth): resolve API key validation issue

Fixes bug where API keys with special characters
were not being validated correctly.

Fixes #456
```

### Syncing with Upstream

```bash
# Add upstream remote (if not already added)
git remote add upstream https://github.com/ORIGINAL_OWNER/WMS_MCP_Server.git

# Fetch upstream changes
git fetch upstream

# Rebase your branch on top of upstream/develop
git rebase upstream/develop
```

## Pull Request Process

### Before Submitting

1. **Run Tests**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

2. **Run Linters**

```bash
# Format code
black app/ tests/

# Check type hints
mypy app/

# Run flake8
flake8 app/ tests/
```

3. **Update Documentation**

- Update relevant documentation files
- Add docstrings to new functions/classes
- Update API documentation if adding/modifying tools

### Submitting a Pull Request

1. **Push Your Branch**

```bash
git push origin feature/your-feature-name
```

2. **Create Pull Request**

- Go to the repository on GitHub
- Click "New Pull Request"
- Select your branch
- Fill in the PR template

3. **PR Template**

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested your changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests passing
- [ ] No linting errors

## Related Issues
Closes #123
```

### PR Review Process

1. **Automated Checks**
   - CI pipeline runs tests
   - Code quality checks
   - Security scanning

2. **Code Review**
   - At least one maintainer must review
   - Address review comments
   - Update PR as needed

3. **Approval and Merge**
   - Get approval from maintainers
   - Resolve all review comments
   - Merge into develop branch

## Coding Standards

### Python Style Guide

We follow PEP 8 with some modifications:

- Use Black for code formatting
- Maximum line length: 100 characters
- Use type hints for all function signatures
- Docstrings for all public functions and classes

### Code Formatting

```bash
# Format code with Black
black app/ tests/

# Check formatting without modifying
black --check app/ tests/
```

### Type Hints

```python
from typing import Optional, List, Dict
from pydantic import BaseModel

class ToolInput(BaseModel):
    sku_code: str
    quantity: int
    location_code: str

async def execute_tool(
    input_data: ToolInput,
    timeout: Optional[int] = None
) -> Dict[str, any]:
    """Execute the tool with given input.
    
    Args:
        input_data: Tool input parameters
        timeout: Optional timeout in seconds
        
    Returns:
        Dictionary with tool execution results
    """
    pass
```

### Docstrings

We use Google-style docstrings:

```python
def calculate_abc_class(turnover_rate: float, value: float) -> str:
    """Calculate ABC classification based on turnover and value.
    
    Args:
        turnover_rate: Annual turnover rate for the SKU
        value: Total value of inventory for the SKU
        
    Returns:
        ABC class ('A', 'B', or 'C')
        
    Raises:
        ValueError: If turnover_rate or value are negative
    """
    if turnover_rate < 0 or value < 0:
        raise ValueError("Turnover rate and value must be positive")
    
    # Implementation
    pass
```

### Error Handling

```python
# Good: Specific error handling
try:
    result = await database.execute(query)
except DatabaseConnectionError as e:
    logger.error(f"Database connection failed: {e}")
    raise
except DatabaseQueryError as e:
    logger.warning(f"Query failed: {e}")
    return None

# Bad: Generic error handling
try:
    result = await database.execute(query)
except Exception as e:
    logger.error(f"Error: {e}")
    raise
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed debugging information")
logger.info("General information about execution")
logger.warning("Warning about potential issues")
logger.error("Error occurred but execution continued")
logger.critical("Critical error requiring immediate attention")

# Include context in logs
logger.info(f"Processing order {order_id} for user {user_id}")
logger.error(f"Failed to update inventory for SKU {sku_code}: {error}")
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/
│   ├── test_inventory_tools.py
│   ├── test_transaction_tools.py
│   └── test_monitoring_tools.py
├── integration/
│   ├── test_database_integration.py
│   ├── test_redis_integration.py
│   └── test_queue_integration.py
└── e2e/
    └── test_workflows.py
```

### Writing Tests

```python
import pytest
from app.tools.inventory.check_stock_availability import CheckStockAvailabilityTool
from app.models.tool_input import CheckStockAvailabilityInput

class TestCheckStockAvailability:
    """Tests for check_stock_availability tool."""
    
    @pytest.fixture
    async def tool(self, db_client):
        """Fixture for tool instance."""
        return CheckStockAvailabilityTool(db_client)
    
    @pytest.mark.asyncio
    async def test_valid_sku_code(self, tool):
        """Test tool with valid SKU code."""
        input_data = CheckStockAvailabilityInput(
            sku_code="SKU-1060-6GB",
            warehouse_id=1
        )
        result = await tool.execute(input_data)
        
        assert result.success is True
        assert "available_quantity" in result.data
    
    @pytest.mark.asyncio
    async def test_invalid_sku_code(self, tool):
        """Test tool with invalid SKU code."""
        input_data = CheckStockAvailabilityInput(
            sku_code="INVALID-SKU",
            warehouse_id=1
        )
        result = await tool.execute(input_data)
        
        assert result.success is False
        assert result.error_code == "NOT_FOUND"
```

### Test Coverage

- Aim for at least 80% code coverage
- Focus on critical paths and business logic
- Test error conditions and edge cases
- Use fixtures for common test setup

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_inventory_tools.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/unit/test_inventory_tools.py::TestCheckStockAvailability::test_valid_sku_code

# Run tests matching pattern
pytest -k "check_stock"
```

## Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include type hints
- Document parameters, return values, and exceptions

### API Documentation

- Update API_REFERENCE.md when adding/modifying tools
- Include request/response examples
- Document error codes
- Update version information

### Tool Documentation

- Update TOOL_GUIDE.md with tool usage examples
- Add step-by-step tutorials for new workflows
- Document tool composition patterns
- Update troubleshooting guides

### Architecture Documentation

- Update ARCHITECTURE.md for architectural changes
- Add new decision records (ADRs) for significant decisions
- Update data flow diagrams
- Document integration points

## Reporting Issues

### Bug Reports

When reporting bugs, include:

1. **Description**
   - Clear description of the bug
   - Steps to reproduce
   - Expected behavior
   - Actual behavior

2. **Environment**
   - Python version
   - Operating system
   - Database version
   - Redis version

3. **Logs and Screenshots**
   - Relevant log output
   - Screenshots if applicable
   - Stack traces

4. **Minimal Reproduction**
   - Minimal code example to reproduce
   - Test case if possible

### Bug Report Template

```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- Python version: 3.13.0
- OS: Ubuntu 22.04
- Database: PostgreSQL 15

## Logs
```
Relevant log output
```

## Additional Context
Any other relevant information
```

## Feature Requests

### Proposing Features

When proposing new features:

1. **Check Existing Issues**
   - Search for similar feature requests
   - Check if feature is already planned

2. **Describe the Feature**
   - Clear description of the feature
   - Use case and motivation
   - Proposed implementation approach
   - Alternative approaches considered

3. **Feature Request Template**

```markdown
## Feature Description
Clear description of the feature

## Motivation
Why is this feature needed?

## Proposed Solution
How should this be implemented?

## Alternatives Considered
What other approaches were considered?

## Additional Context
Any other relevant information
```

### Feature Discussion

- Open an issue with the feature request template
- Discuss with maintainers and community
- Get approval before implementing
- Create a feature branch after approval

## Development Guidelines

### Adding New Tools

When adding a new tool:

1. **Create Tool File**
   - Place in appropriate directory under `app/tools/`
   - Inherit from `BaseTool`
   - Implement `execute` method
   - Define input schema with Pydantic

2. **Register Tool**
   - Add to tool registry
   - Update tool metadata
   - Add to documentation

3. **Add Tests**
   - Unit tests for tool logic
   - Integration tests for database interactions
   - Error condition tests

4. **Update Documentation**
   - Add to API_REFERENCE.md
   - Add usage examples to TOOL_GUIDE.md
   - Update Modules.md if needed

### Modifying Existing Tools

When modifying existing tools:

1. **Understand Impact**
   - Review tool usage across codebase
   - Check for breaking changes
   - Consider backward compatibility

2. **Update Tests**
   - Update existing tests
   - Add tests for new functionality
   - Ensure all tests pass

3. **Update Documentation**
   - Update API documentation
   - Update usage examples
   - Document breaking changes

### Database Changes

When making database changes:

1. **Create Migration**
   - Use Alembic for migrations
   - Write reversible migration
   - Test migration on copy of production data

2. **Update Models**
   - Update SQLAlchemy models
   - Update Pydantic schemas
   - Update related queries

3. **Document Changes**
   - Update schema documentation
   - Note breaking changes
   - Update deployment procedures

## Release Process

Contributors should not create releases. Releases are managed by maintainers following the process in RELEASE.md.

## Community Guidelines

### Communication

- Be respectful and constructive
- Ask questions in issues or discussions
- Participate in code reviews
- Help other contributors

### Recognition

Contributors are recognized in:
- Release notes
- CONTRIBUTORS file
- Project documentation

### Getting Help

- Check existing documentation
- Search existing issues
- Ask in discussions
- Contact maintainers

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have questions about contributing:
- Check existing documentation
- Open a discussion
- Contact maintainers

Thank you for contributing to WMS MCP Server!
