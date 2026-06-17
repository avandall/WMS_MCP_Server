"""Unit tests for check_redis_locks tool"""

import pytest
from app.tools.monitoring.check_redis_locks import CheckRedisLocks, CheckRedisLocksInput
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_check_redis_locks_found(mock_redis_client, test_config):
    """Test successful lock check when lock exists"""
    # Setup mock
    mock_redis_client.check_lock.return_value = {
        "lock_key": "lock:sku:SKU-TEST-001",
        "lock_value": "test-value",
        "ttl_seconds": 25
    }
    mock_redis_client.get_all_locks.return_value = [
        {
            "lock_key": "lock:sku:SKU-TEST-001",
            "lock_value": "test-value",
            "ttl_seconds": 25
        }
    ]
    
    # Create tool instance
    tool = CheckRedisLocks(test_config)
    tool.redis = mock_redis_client
    
    # Execute tool
    result = await tool.execute(resource_key="lock:sku:SKU-TEST-001")
    
    # Assertions
    assert result.success == True
    assert result.data["specific_lock"] is not None
    assert result.data["specific_lock"]["lock_key"] == "lock:sku:SKU-TEST-001"
    assert result.data["total_related_locks"] == 1
    assert mock_redis_client.check_lock.called


@pytest.mark.asyncio
async def test_check_redis_locks_not_found(mock_redis_client, test_config):
    """Test lock check when lock doesn't exist"""
    # Setup mock
    mock_redis_client.check_lock.return_value = None
    mock_redis_client.get_all_locks.return_value = []
    
    # Create tool instance
    tool = CheckRedisLocks(test_config)
    tool.redis = mock_redis_client
    
    # Execute tool
    result = await tool.execute(resource_key="lock:sku:SKU-NOT-FOUND")
    
    # Assertions
    assert result.success == True
    assert result.data["specific_lock"] is None
    assert result.data["total_related_locks"] == 0
    assert result.data["analysis"]["has_active_lock"] == False


@pytest.mark.asyncio
async def test_check_redis_locks_multiple_locks(mock_redis_client, test_config):
    """Test lock check with multiple related locks"""
    # Setup mock
    mock_redis_client.check_lock.return_value = {
        "lock_key": "lock:sku:SKU-TEST-001",
        "lock_value": "test-value",
        "ttl_seconds": 20
    }
    mock_redis_client.get_all_locks.return_value = [
        {
            "lock_key": "lock:sku:SKU-TEST-001",
            "lock_value": "test-value",
            "ttl_seconds": 20
        },
        {
            "lock_key": "lock:sku:SKU-TEST-001:backup",
            "lock_value": "test-value-2",
            "ttl_seconds": 25
        }
    ]
    
    # Create tool instance
    tool = CheckRedisLocks(test_config)
    tool.redis = mock_redis_client
    
    # Execute tool
    result = await tool.execute(resource_key="lock:sku:SKU-TEST-001")
    
    # Assertions
    assert result.success == True
    assert result.data["total_related_locks"] == 2
    assert result.data["analysis"]["potential_deadlock"] == True


@pytest.mark.asyncio
async def test_check_redis_locks_analysis_stale_lock(mock_redis_client, test_config):
    """Test lock analysis with stale lock"""
    # Setup mock with stale lock (no TTL)
    mock_redis_client.check_lock.return_value = {
        "lock_key": "lock:sku:SKU-TEST-001",
        "lock_value": "test-value",
        "ttl_seconds": -1
    }
    mock_redis_client.get_all_locks.return_value = [
        {
            "lock_key": "lock:sku:SKU-TEST-001",
            "lock_value": "test-value",
            "ttl_seconds": -1
        }
    ]
    
    # Create tool instance
    tool = CheckRedisLocks(test_config)
    tool.redis = mock_redis_client
    
    # Execute tool
    result = await tool.execute(resource_key="lock:sku:SKU-TEST-001")
    
    # Assertions
    assert result.success == True
    assert "stale" in result.data["analysis"]["recommendation"].lower()


@pytest.mark.asyncio
async def test_check_redis_locks_input_validation():
    """Test Pydantic input validation"""
    # Valid input
    valid_input = CheckRedisLocksInput(
        resource_key="lock:sku:SKU-TEST-001"
    )
    assert valid_input.resource_key == "lock:sku:SKU-TEST-001"
    
    # Invalid input (missing required field)
    with pytest.raises(Exception):
        CheckRedisLocksInput()


@pytest.mark.asyncio
async def test_check_redis_locks_get_input_schema(test_config):
    """Test input schema generation"""
    tool = CheckRedisLocks(test_config)
    schema = tool.get_input_schema()
    
    assert schema["type"] == "object"
    assert "resource_key" in schema["properties"]
    assert "resource_key" in schema["required"]
