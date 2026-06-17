"""Unit tests for update_inventory_quantity tool"""

import pytest
from app.tools.transactions.update_inventory_quantity import UpdateInventoryQuantity, UpdateInventoryQuantityInput
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_update_inventory_quantity_increase(mock_db_client, mock_redis_client, test_config):
    """Test successful inventory quantity increase"""
    # Setup mocks
    mock_db_client.update_stock_quantity.return_value = True
    mock_redis_client.acquire_lock.return_value = True
    mock_redis_client.release_lock.return_value = True
    mock_redis_client.cache_delete.return_value = True
    
    # Create tool instance
    tool = UpdateInventoryQuantity(test_config)
    tool.db = mock_db_client
    tool.redis = mock_redis_client
    
    # Execute tool
    result = await tool.execute(
        sku_code="SKU-TEST-001",
        location_code="ZONE-A-ROW-01-SHELF-01",
        action="INCREASE",
        quantity=50
    )
    
    # Assertions
    assert result.success == True
    assert result.data["action"] == "INCREASE"
    assert result.data["quantity"] == 50
    assert mock_db_client.update_stock_quantity.called
    assert mock_redis_client.acquire_lock.called
    assert mock_redis_client.release_lock.called


@pytest.mark.asyncio
async def test_update_inventory_quantity_decrease(mock_db_client, mock_redis_client, test_config):
    """Test successful inventory quantity decrease"""
    # Setup mocks
    mock_db_client.update_stock_quantity.return_value = True
    mock_redis_client.acquire_lock.return_value = True
    mock_redis_client.release_lock.return_value = True
    mock_redis_client.cache_delete.return_value = True
    
    # Create tool instance
    tool = UpdateInventoryQuantity(test_config)
    tool.db = mock_db_client
    tool.redis = mock_redis_client
    
    # Execute tool
    result = await tool.execute(
        sku_code="SKU-TEST-001",
        location_code="ZONE-A-ROW-01-SHELF-01",
        action="DECREASE",
        quantity=30
    )
    
    # Assertions
    assert result.success == True
    assert result.data["action"] == "DECREASE"
    assert result.data["quantity"] == 30


@pytest.mark.asyncio
async def test_update_inventory_quantity_lock_failure(mock_db_client, mock_redis_client, test_config):
    """Test handling when lock acquisition fails"""
    # Setup mocks
    mock_redis_client.acquire_lock.return_value = False
    
    # Create tool instance
    tool = UpdateInventoryQuantity(test_config)
    tool.db = mock_db_client
    tool.redis = mock_redis_client
    
    # Execute tool
    result = await tool.execute(
        sku_code="SKU-TEST-001",
        location_code="ZONE-A-ROW-01-SHELF-01",
        action="INCREASE",
        quantity=50
    )
    
    # Assertions
    assert result.success == False
    assert "lock" in result.error.lower()
    assert result.error_code == "LOCK_ACQUISITION_FAILED"
    assert not mock_db_client.update_stock_quantity.called


@pytest.mark.asyncio
async def test_update_inventory_quantity_invalid_action(test_config):
    """Test with invalid action"""
    # Create tool instance
    tool = UpdateInventoryQuantity(test_config)
    
    # Execute tool with invalid action
    result = await tool.execute(
        sku_code="SKU-TEST-001",
        location_code="ZONE-A-ROW-01-SHELF-01",
        action="INVALID_ACTION",
        quantity=50
    )
    
    # Assertions
    assert result.success == False
    assert result.error_code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_update_inventory_quantity_zero_quantity(test_config):
    """Test with zero quantity (should fail)"""
    # Create tool instance
    tool = UpdateInventoryQuantity(test_config)
    
    # Execute tool with zero quantity
    result = await tool.execute(
        sku_code="SKU-TEST-001",
        location_code="ZONE-A-ROW-01-SHELF-01",
        action="INCREASE",
        quantity=0
    )
    
    # Assertions
    assert result.success == False
    assert result.error_code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_update_inventory_quantity_input_validation():
    """Test Pydantic input validation"""
    # Valid input
    valid_input = UpdateInventoryQuantityInput(
        sku_code="SKU-TEST-001",
        location_code="ZONE-A-ROW-01-SHELF-01",
        action="INCREASE",
        quantity=50
    )
    assert valid_input.sku_code == "SKU-TEST-001"
    assert valid_input.action == "INCREASE"
    assert valid_input.quantity == 50
    
    # Invalid action
    with pytest.raises(Exception):
        UpdateInventoryQuantityInput(
            sku_code="SKU-TEST-001",
            location_code="ZONE-A-ROW-01-SHELF-01",
            action="INVALID",
            quantity=50
        )
