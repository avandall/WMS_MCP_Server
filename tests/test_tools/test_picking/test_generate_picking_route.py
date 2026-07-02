"""Unit tests for generate_picking_route tool"""

import pytest
from app.tools.picking.generate_picking_route import GeneratePickingRoute
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_generate_picking_route_success(mock_db_client, test_config):
    """Test successful picking route optimization"""
    items_locations_mock = [
        {
            "sku_code": "SKU-TEST-001",
            "quantity": 2,
            "location_code": "ZONE-A-ROW-01-SHELF-01",
            "zone_id": "ZONE-A",
            "row_id": "ROW-01",
            "shelf_id": "SHELF-01",
            "x_coordinate": 0.0,
            "y_coordinate": 0.0,
            "z_coordinate": 0.0,
            "available_qty": 10
        },
        {
            "sku_code": "SKU-TEST-002",
            "quantity": 1,
            "location_code": "ZONE-A-ROW-01-SHELF-02",
            "zone_id": "ZONE-A",
            "row_id": "ROW-01",
            "shelf_id": "SHELF-02",
            "x_coordinate": 0.0,
            "y_coordinate": 5.0,
            "z_coordinate": 0.0,
            "available_qty": 5
        },
        {
            "sku_code": "SKU-TEST-003",
            "quantity": 3,
            "location_code": "ZONE-B-ROW-02-SHELF-01",
            "zone_id": "ZONE-B",
            "row_id": "ROW-02",
            "shelf_id": "SHELF-01",
            "x_coordinate": 10.0,
            "y_coordinate": 10.0,
            "z_coordinate": 0.0,
            "available_qty": 20
        }
    ]
    
    mock_db_client.fetch_many.return_value = items_locations_mock
    
    tool = GeneratePickingRoute(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-TEST-001")
    
    assert result.success is True
    assert result.data["order_id"] == "ORD-TEST-001"
    assert result.data["total_items"] == 3
    assert result.data["unique_locations"] == 3
    
    route = result.data["optimized_route"]
    assert len(route) == 3
    
    # Distance between:
    # 1: (0, 0, 0) and 2: (0, 5, 0) is 5.0
    # 2: (0, 5, 0) and 3: (10, 10, 0) is sqrt(100 + 25) = 11.18
    # Total distance: 5.0 + 11.18 = 16.18
    metrics = result.data["route_metrics"]
    assert metrics["total_distance_m"] == 16.18
    
    instructions = result.data["picking_instructions"]
    assert len(instructions) == 3
    assert instructions[0]["stop_number"] == 1
    assert instructions[0]["location_code"] == "ZONE-A-ROW-01-SHELF-01"


@pytest.mark.asyncio
async def test_generate_picking_route_not_found(mock_db_client, test_config):
    """Test when no available items are found for order"""
    mock_db_client.fetch_many.return_value = []
    
    tool = GeneratePickingRoute(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-EMPTY")
    
    assert result.success is False
    assert result.error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_generate_picking_route_invalid_id(test_config):
    """Test with invalid order ID"""
    tool = GeneratePickingRoute(test_config)
    
    result = await tool.execute(order_id="")
    
    assert result.success is False
    assert result.error_code == "VALIDATION_ERROR"
