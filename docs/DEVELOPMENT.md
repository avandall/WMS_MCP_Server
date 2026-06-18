# Development Setup Guide

This guide provides comprehensive instructions for setting up a development environment for the WMS MCP Server.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Setup](#environment-setup)
- [Database Setup](#database-setup)
- [Redis Setup](#redis-setup)
- [Message Queue Setup](#message-queue-setup)
- [Running the Server](#running-the-server)
- [Testing](#testing)
- [Debugging](#debugging)
- [Common Development Tasks](#common-development-tasks)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Python**: 3.13 or higher
- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **Git**: 2.30 or higher
- **Make**: (optional, for convenience)

### Recommended Tools

- **Virtual Environment**: venv or conda
- **IDE**: VS Code, PyCharm, or similar
- **PostgreSQL Client**: psql or pgAdmin
- **Redis Client**: redis-cli
- **API Client**: Postman or Insomnia

### System Requirements

- **RAM**: Minimum 8GB (16GB recommended)
- **Disk Space**: Minimum 20GB free
- **CPU**: 4 cores minimum

## Quick Start

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/WMS_MCP_Server.git
cd WMS_MCP_Server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Start development services
docker-compose up -d postgres redis rabbitmq

# Run database migrations
python -m alembic upgrade head

# Run tests
pytest
```

### Verify Installation

```bash
# Check Python version
python --version  # Should be 3.13+

# Check installed packages
pip list

# Test server startup
python -m app.server --help
```

## Environment Setup

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://wms_user:wms_password@localhost:5432/wms_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_LOCK_TTL=300

# Message Queue
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_QUEUE_PREFIX=wms

# Server
WMS_API_KEY=dev-api-key-12345
WMS_HOST=0.0.0.0
WMS_PORT=8000
WMS_LOG_LEVEL=DEBUG

# External Services
DHL_API_KEY=your-dhl-api-key
FEDEX_API_KEY=your-fedex-api-key
UPS_API_KEY=your-ups-api-key
GHTK_API_KEY=your-ghtk-api-key
GHN_API_KEY=your-ghn-api-key
```

### Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Deactivate virtual environment
deactivate
```

### Dependency Installation

```bash
# Install core dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Install specific dependency groups
pip install -e ".[test]"    # Testing tools
pip install -e ".[lint]"    # Linting tools
pip install -e ".[docs]"    # Documentation tools
```

## Database Setup

### Using Docker Compose (Recommended)

```bash
# Start PostgreSQL container
docker-compose up -d postgres

# Check container status
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Connect to database
docker-compose exec postgres psql -U wms_user -d wms_db
```

### Manual PostgreSQL Setup

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql
```

```sql
-- Create user
CREATE USER wms_user WITH PASSWORD 'wms_password';

-- Create database
CREATE DATABASE wms_db OWNER wms_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE wms_db TO wms_user;

-- Exit
\q
```

### Database Migrations

```bash
# Run all migrations
python -m alembic upgrade head

# Run specific migration
python -m alembic upgrade +1

# Rollback migration
python -m alembic downgrade -1

# Create new migration
python -m alembic revision --autogenerate -m "description"

# View migration history
python -m alembic history

# View current version
python -m alembic current
```

### Seed Data

```bash
# Load seed data
python scripts/seed_database.py

# Load test data
python scripts/load_test_data.py
```

## Redis Setup

### Using Docker Compose (Recommended)

```bash
# Start Redis container
docker-compose up -d redis

# Check container status
docker-compose ps redis

# View logs
docker-compose logs redis

# Connect to Redis
docker-compose exec redis redis-cli
```

### Manual Redis Setup

```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install redis-server

# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping  # Should return PONG
```

### Redis Configuration

```bash
# Connect to Redis CLI
redis-cli

# Test connection
ping

# View all keys
KEYS *

# View specific key
GET key_name

# Delete key
DEL key_name

# Flush all data (use with caution)
FLUSHALL
```

## Message Queue Setup

### Using Docker Compose (Recommended)

```bash
# Start RabbitMQ container
docker-compose up -d rabbitmq

# Check container status
docker-compose ps rabbitmq

# View logs
docker-compose logs rabbitmq

# Access RabbitMQ Management UI
# Open: http://localhost:15672
# Username: guest
# Password: guest
```

### Manual RabbitMQ Setup

```bash
# Install RabbitMQ (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install rabbitmq-server

# Start RabbitMQ service
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Restart service
sudo systemctl restart rabbitmq-server
```

### Queue Management

```bash
# Access RabbitMQ Management UI
# http://localhost:15672

# Create queues via CLI
rabbitmqadmin declare queue name=wms.order.process durable=true
rabbitmqadmin declare queue name=wms.inventory.update durable=true
rabbitmqadmin declare queue name=wms.shipping.label durable=true

# View queues
rabbitmqadmin list queues

# Purge queue
rabbitmqadmin purge queue name=wms.order.process
```

## Running the Server

### Development Server

```bash
# Start server with stdio transport
python -m app.server

# Start server with SSE transport
python -m app.server --transport sse --port 8000

# Start with custom configuration
python -m app.server --config config/development.py
```

### Using Docker

```bash
# Build Docker image
docker build -t wms-mcp-server:dev .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  wms-mcp-server:dev

# Run with Docker Compose
docker-compose up wms_server
```

### Server Configuration

Create `config/development.py`:

```python
import os
from pydantic_settings import BaseSettings

class DevelopmentSettings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    DATABASE_POOL_SIZE: int = 20
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL")
    REDIS_LOCK_TTL: int = 300
    
    # Message Queue
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL")
    
    # Server
    WMS_API_KEY: str = os.getenv("WMS_API_KEY")
    WMS_HOST: str = "0.0.0.0"
    WMS_PORT: int = 8000
    WMS_LOG_LEVEL: str = "DEBUG"
    
    # External Services
    DHL_API_KEY: str = os.getenv("DHL_API_KEY", "")
    
    class Config:
        env_file = ".env"

settings = DevelopmentSettings()
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_inventory_tools.py

# Run specific test
pytest tests/unit/test_inventory_tools.py::TestCheckStockAvailability::test_valid_sku

# Run with verbose output
pytest -v

# Run with debugging
pytest --pdb
```

### Test Configuration

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=app
    --cov-report=term-missing
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
```

### Test Database

```bash
# Create test database
createdb wms_test_db

# Run migrations on test database
DATABASE_URL=postgresql://wms_user:wms_password@localhost:5432/wms_test_db \
  python -m alembic upgrade head

# Run tests with test database
DATABASE_URL=postgresql://wms_user:wms_password@localhost:5432/wms_test_db \
  pytest
```

## Debugging

### VS Code Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: MCP Server",
      "type": "python",
      "request": "launch",
      "module": "app.server",
      "args": [],
      "envFile": "${workspaceFolder}/.env",
      "console": "integratedTerminal",
      "justMyCode": false
    },
    {
      "name": "Python: Run Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "-v",
        "--pdb"
      ],
      "envFile": "${workspaceFolder}/.env",
      "console": "integratedTerminal"
    }
  ]
}
```

### PyCharm Configuration

1. **Run Configuration**:
   - Go to Run > Edit Configurations
   - Add Python configuration
   - Module name: `app.server`
   - Environment variables: Load from `.env`

2. **Test Configuration**:
   - Add pytest configuration
   - Target: tests directory
   - Additional arguments: `-v`

### Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Use in code
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Debugging Tools

```bash
# Use pdb for debugging
python -m pdb app/server.py

# Use ipdb (enhanced pdb)
pip install ipdb
python -m ipdb app/server.py

# Use pudb (visual debugger)
pip install pudb
python -m pudb app/server.py
```

## Common Development Tasks

### Adding a New Tool

1. **Create Tool File**:

```bash
# Create tool file
touch app/tools/inventory/new_tool.py
```

2. **Implement Tool**:

```python
from app.tools.base import BaseTool
from pydantic import BaseModel, Field
from typing import Optional

class NewToolInput(BaseModel):
    """Input schema for new tool."""
    sku_code: str = Field(..., description="SKU code")
    quantity: int = Field(..., ge=0, description="Quantity")

class NewTool(BaseTool):
    """New tool description."""
    
    name = "new_tool"
    description = "Tool description"
    
    async def execute(self, input_data: NewToolInput) -> dict:
        """Execute the tool."""
        # Implementation
        return {"success": True, "data": {}}
```

3. **Register Tool**:

```python
# In app/registry.py
from app.tools.inventory.new_tool import NewTool

registry.register_tool(NewTool)
```

4. **Add Tests**:

```python
# tests/unit/test_new_tool.py
import pytest
from app.tools.inventory.new_tool import NewTool, NewToolInput

class TestNewTool:
    @pytest.mark.asyncio
    async def test_execute(self):
        tool = NewTool()
        input_data = NewToolInput(sku_code="SKU-001", quantity=10)
        result = await tool.execute(input_data)
        assert result["success"] is True
```

### Database Query

```python
import asyncpg

async def query_database():
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Execute query
        rows = await conn.fetch(
            "SELECT * FROM inventory WHERE sku_code = $1",
            "SKU-1060-6GB"
        )
        
        for row in rows:
            print(row)
            
    finally:
        await conn.close()
```

### Redis Operations

```python
import aioredis

async def redis_operations():
    redis = aioredis.from_url(REDIS_URL)
    
    try:
        # Set value
        await redis.set("key", "value", ex=300)
        
        # Get value
        value = await redis.get("key")
        print(value)
        
        # Delete key
        await redis.delete("key")
        
    finally:
        await redis.close()
```

### Message Queue Operations

```python
import aio_pika
import json

async def publish_message():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    
    await channel.default_exchange.publish(
        aio_pika.Message(body=json.dumps({"key": "value"})),
        routing_key="wms.order.process"
    )
    
    await connection.close()
```

## Troubleshooting

### Common Issues

#### Database Connection Failed

**Symptoms**: `DATABASE_ERROR` when running tools

**Solutions**:
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Verify connection string
echo $DATABASE_URL

# Test connection manually
psql $DATABASE_URL
```

#### Redis Connection Failed

**Symptoms**: `REDIS_ERROR` when running tools

**Solutions**:
```bash
# Check Redis is running
docker-compose ps redis

# Check logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis

# Test connection
redis-cli ping
```

#### RabbitMQ Connection Failed

**Symptoms**: `QUEUE_ERROR` when running tools

**Solutions**:
```bash
# Check RabbitMQ is running
docker-compose ps rabbitmq

# Check logs
docker-compose logs rabbitmq

# Restart RabbitMQ
docker-compose restart rabbitmq

# Check management UI
# http://localhost:15672
```

#### Port Already in Use

**Symptoms**: `Address already in use` error

**Solutions**:
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
python -m app.server --port 8001
```

#### Import Errors

**Symptoms**: `ModuleNotFoundError` or `ImportError`

**Solutions**:
```bash
# Reinstall dependencies
pip install -e ".[dev]"

# Check Python path
python -c "import sys; print(sys.path)"

# Verify virtual environment is activated
which python
```

### Getting Help

If you encounter issues not covered here:

1. Check the documentation:
   - [API_REFERENCE.md](API_REFERENCE.md)
   - [TOOL_GUIDE.md](TOOL_GUIDE.md)
   - [ERROR_HANDLING.md](ERROR_HANDLING.md)

2. Search existing issues on GitHub

3. Create a new issue with:
   - Error message
   - Steps to reproduce
   - Environment details
   - Relevant logs

### Development Tips

1. **Use Makefile for Common Tasks**:

```makefile
# Makefile
.PHONY: help install test lint format clean

help:
	@echo "Available commands:"
	@echo "  make install   - Install dependencies"
	@echo "  make test      - Run tests"
	@echo "  make lint      - Run linters"
	@echo "  make format    - Format code"
	@echo "  make clean     - Clean up"

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	mypy app/
	flake8 app/ tests/

format:
	black app/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
```

2. **Use Pre-commit Hooks**:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
EOF

# Install hooks
pre-commit install
```

3. **Monitor Resource Usage**:

```bash
# Monitor Docker containers
docker stats

# Monitor PostgreSQL connections
docker-compose exec postgres psql -U wms_user -d wms_db -c "SELECT count(*) FROM pg_stat_activity;"

# Monitor Redis memory
docker-compose exec redis redis-cli INFO memory
```

## Next Steps

After setting up your development environment:

1. Read the [API_REFERENCE.md](API_REFERENCE.md) to understand available tools
2. Review the [TOOL_GUIDE.md](TOOL_GUIDE.md) for usage examples
3. Check the [ARCHITECTURE.md](ARCHITECTURE.md) for system architecture
4. Explore the codebase and start contributing!

Happy coding!
