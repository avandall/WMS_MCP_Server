"""Unit tests for inspect_shelf_capacity tool"""

import pytest
from app.tools.inventory.inspect_shelf_capacity import InspectShelfCapacity, InspectShelfCapacityInput
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_inspect_shelf_capacity_success(mock_db_client, test_config, sample_location_data):
    """Test successful shelf capacity inspection"""
    # Setup mock
    mock_db_client.fetch_one.return_value = sample_location_data
    
    # Create tool instance
    tool = InspectShelfCapacity(test_config)
    tool.db = mock_db_client
    
    # Execute tool
    result = await tool.execute(location_code="ZONE-A-ROW-01-SHELF-01")
    
    # Assertions
    assert result.success == True
    assert result.data["location_code"] == "ZONE-A-ROW-01-SHELF-01"
    assert result.data["available_volume"] == 5000.0
    assert "volume_utilization_percent" in result.data
    assert mock_db_client.fetch_one.called


@pytest.mark.asyncio
async def test_inspect_shelf_capacity_not_found(mock_db_client, test_config):
    """Test shelf capacity inspection when location not found"""
    # Setup mock
    mock_db_client.fetch_one.return_value = None
    
    # Create tool instance
    tool = InspectShelfCapacity(test_config)
    tool.db = mock_db_client
    
    # Execute tool
    result = await tool.execute(location_code="ZONE-NOT-FOUND")
    
    # Assertions
    assert result.success == False
    assert "not found" in result.error.lower()
    assert result.error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_inspect_shelf_capacity_utilization_calculation(mock_db_client, test_config):
    """Test utilization percentage calculation"""
    # Setup mock with specific data
    location_data = {
        "location_code": "ZONE-A-ROW-01-SHELF-01",
        "max_volume": 10000.0,
        "current_volume": 7500.0,
        "max_weight": 500.0,
        "current_weight": 400.0
    }
    mock_db_client.fetch_one.return_value = location_data
    
    # Create tool instance
    tool = InspectShelfCapacity(test_config)
    tool.db = mock_db_client
    
    # Execute tool
    result = await tool.execute(location_code="ZONE-A-ROW-01-SHELF-01")
    
    # Assertions
    assert result.success == True
    assert result.data["volume_utilization_percent"] == 75.0
    assert result.data["weight_utilization_percent"] == 80.0


@pytest.mark.asyncio
async def test_inspect_shelf_capacity_invalid_location(test_config):
    """Test shelf capacity inspection with invalid location code"""
    # Create tool instance
    tool = InspectShelfCapacity(test_config)
    
    # Execute tool with invalid location (empty string)
    result = await tool.execute(location_code="")
    
    # Assertions
    assert result.success == False
    assert result.error_code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_inspect_shelf_capacity_input_validation():
    """Test Pydantic input validation"""
    # Valid input
    valid_input = InspectShelfCapacityInput(
        location_code="ZONE-A-ROW-01-SHELF-01"
    )
    assert valid_input.location_code == "ZONE-A-ROW-01-SHELF-01"
    
    # Invalid input (missing required field)
    with pytest.raises(Exception):
        InspectShelfCapacityInput()


@pytest.mark.asyncio
async def test_inspect_shelf_capacity_get_input_schema(test_config):
    """Test input schema generation"""
    tool = InspectShelfCapacity(test_config)
    schema = tool.get_input_schema()
    
    assert schema["type"] == "object"
    assert "location_code" in schema["properties"]
    assert "location_code" in schema["required"]
