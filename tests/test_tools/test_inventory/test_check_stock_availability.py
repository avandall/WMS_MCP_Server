"""Unit tests for check_stock_availability tool"""

import pytest
from app.tools.inventory.check_stock_availability import CheckStockAvailability, CheckStockAvailabilityInput
from app.tools.base import ToolResult
from app.tools.base import ToolError


@pytest.mark.asyncio
async def test_check_stock_availability_success(mock_db_client, test_config, sample_stock_data):
    """Test successful stock availability check"""
    # Setup mock
    mock_db_client.fetch_one.return_value = sample_stock_data
    
    # Create tool instance
    tool = CheckStockAvailability(test_config)
    tool.db = mock_db_client
    
    # Execute tool
    result = await tool.execute(sku_code="SKU-TEST-001", warehouse_id=1)
    
    # Assertions
    assert result.success == True
    assert result.data["sku_code"] == "SKU-TEST-001"
    assert result.data["available_qty"] == 80
    assert mock_db_client.fetch_one.called


@pytest.mark.asyncio
async def test_check_stock_availability_not_found(mock_db_client, test_config):
    """Test stock availability check when SKU not found"""
    # Setup mock
    mock_db_client.fetch_one.return_value = None
    
    # Create tool instance
    tool = CheckStockAvailability(test_config)
    tool.db = mock_db_client
    
    # Execute tool
    result = await tool.execute(sku_code="SKU-NOT-FOUND")
    
    # Assertions
    assert result.success == False
    assert "not found" in result.error.lower()
    assert result.error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_check_stock_availability_invalid_sku(test_config):
    """Test stock availability check with invalid SKU"""
    # Create tool instance
    tool = CheckStockAvailability(test_config)
    
    # Execute tool with invalid SKU (empty string)
    result = await tool.execute(sku_code="")
    
    # Assertions
    assert result.success == False
    assert result.error_code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_check_stock_availability_invalid_warehouse_id(test_config):
    """Test stock availability check with invalid warehouse ID"""
    # Create tool instance
    tool = CheckStockAvailability(test_config)
    
    # Execute tool with invalid warehouse ID (negative)
    result = await tool.execute(sku_code="SKU-TEST-001", warehouse_id=-1)
    
    # Assertions
    assert result.success == False
    assert result.error_code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_check_stock_availability_input_validation():
    """Test Pydantic input validation"""
    # Valid input
    valid_input = CheckStockAvailabilityInput(
        sku_code="SKU-TEST-001",
        warehouse_id=1
    )
    assert valid_input.sku_code == "SKU-TEST-001"
    assert valid_input.warehouse_id == 1
    
    # Valid input without warehouse_id
    valid_input_optional = CheckStockAvailabilityInput(sku_code="SKU-TEST-001")
    assert valid_input_optional.sku_code == "SKU-TEST-001"
    assert valid_input_optional.warehouse_id is None
    
    # Invalid input (missing required field)
    with pytest.raises(Exception):
        CheckStockAvailabilityInput()


@pytest.mark.asyncio
async def test_check_stock_availability_get_input_schema(test_config):
    """Test input schema generation"""
    tool = CheckStockAvailability(test_config)
    schema = tool.get_input_schema()
    
    assert schema["type"] == "object"
    assert "sku_code" in schema["properties"]
    assert "warehouse_id" in schema["properties"]
    assert "sku_code" in schema["required"]
    assert "warehouse_id" not in schema["required"]


@pytest.mark.asyncio
async def test_check_stock_availability_database_error(mock_db_client, test_config):
    """Test handling of database errors"""
    # Setup mock to raise exception
    mock_db_client.fetch_one.side_effect = Exception("Database connection failed")
    
    # Create tool instance
    tool = CheckStockAvailability(test_config)
    tool.db = mock_db_client
    
    # Execute tool
    result = await tool.execute(sku_code="SKU-TEST-001")
    
    # Assertions
    assert result.success == False
    assert "Database connection failed" in result.error
