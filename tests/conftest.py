"""Test configuration and fixtures"""

import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from app.config import Config
from app.tools.registry import ToolRegistry
from app.clients.database_client import DatabaseClient
from app.clients.redis_client import RedisClient
from app.clients.queue_client import QueueClient


@pytest.fixture
def test_config() -> Config:
    """Test configuration"""
    return Config(
        DATABASE_URL="sqlite://:memory:",
        REDIS_URL="redis://localhost:6379/1",
        RABBITMQ_URL="amqp://guest:guest@localhost:5672/",
        DEBUG=True,
        LOG_LEVEL="DEBUG",
        CACHE_ENABLED=False,
        RATE_LIMIT_ENABLED=False
    )


@pytest.fixture
def test_registry() -> ToolRegistry:
    """Test tool registry"""
    return ToolRegistry()


@pytest.fixture
async def mock_db_client(test_config: Config) -> AsyncGenerator[DatabaseClient, None]:
    """Mock database client for testing"""
    client = DatabaseClient(test_config)
    
    # Mock the connect method
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    
    # Mock common database methods
    client.fetch_one = AsyncMock()
    client.fetch_many = AsyncMock(return_value=[])
    client.fetch_val = AsyncMock()
    client.execute = AsyncMock(return_value="SELECT 1")
    client.execute_transaction = AsyncMock(return_value=True)
    client.update_stock_quantity = AsyncMock(return_value=True)
    
    yield client
    
    # Cleanup
    await client.disconnect()


@pytest.fixture
async def mock_redis_client(test_config: Config) -> AsyncGenerator[RedisClient, None]:
    """Mock Redis client for testing"""
    client = RedisClient(test_config)
    
    # Mock the connect method
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    
    # Mock common Redis methods
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=True)
    client.exists = AsyncMock(return_value=False)
    client.acquire_lock = AsyncMock(return_value=True)
    client.release_lock = AsyncMock(return_value=True)
    client.check_lock = AsyncMock(return_value=None)
    client.get_all_locks = AsyncMock(return_value=[])
    client.cache_get = AsyncMock(return_value=None)
    client.cache_set = AsyncMock(return_value=True)
    client.cache_delete = AsyncMock(return_value=True)
    
    yield client
    
    # Cleanup
    await client.disconnect()


@pytest.fixture
async def mock_queue_client(test_config: Config) -> AsyncGenerator[QueueClient, None]:
    """Mock queue client for testing"""
    client = QueueClient(test_config)
    
    # Mock the connect method
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    
    # Mock common queue methods
    client.publish_message = AsyncMock(return_value=True)
    client.get_queue_status = AsyncMock(return_value={
        "queue_name": "test",
        "message_count": 0,
        "consumer_count": 0
    })
    client.get_order_queue_backlog = AsyncMock(return_value={})
    
    yield client
    
    # Cleanup
    await client.disconnect()


@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing"""
    return {
        "sku_code": "SKU-TEST-001",
        "warehouse_id": 1,
        "physical_qty": 100,
        "available_qty": 80,
        "reserved_qty": 20,
        "location_code": "ZONE-A-ROW-01-SHELF-01",
        "last_updated": "2024-01-01T00:00:00"
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing"""
    return {
        "order_id": "ORD-TEST-001",
        "customer_id": "CUST-001",
        "customer_name": "Test Customer",
        "status": "CONFIRMED",
        "total_amount": 1000.00,
        "items": [
            {
                "sku_code": "SKU-TEST-001",
                "quantity": 10,
                "unit_price": 100.00
            }
        ]
    }


@pytest.fixture
def sample_location_data():
    """Sample location data for testing"""
    return {
        "location_code": "ZONE-A-ROW-01-SHELF-01",
        "zone_id": "ZONE-A",
        "row_id": "ROW-01",
        "shelf_id": "SHELF-01",
        "max_volume": 10000.0,
        "max_weight": 500.0,
        "current_volume": 5000.0,
        "current_weight": 250.0,
        "available_volume": 5000.0,
        "available_weight": 250.0
    }



