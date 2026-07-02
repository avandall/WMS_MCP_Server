"""Unit tests for suggest_packing_box tool"""

import pytest
from app.tools.orders.suggest_packing_box import SuggestPackingBox
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_suggest_packing_box_success(mock_db_client, test_config):
    """Test successful box packing recommendation"""
    order_items_mock = [
        {
            "sku_code": "SKU-TEST-001",
            "quantity": 2,
            "length": 10.0,
            "width": 5.0,
            "height": 3.0,
            "weight": 1.5,
            "item_volume": 150.0,
            "total_weight": 3.0
        }
    ]
    # Total volume: 150.0 * 2 = 300.0 cm3
    # Total weight: 3.0 kg
    
    boxes_mock = [
        {
            "box_id": "BOX-S",
            "name": "Small Box",
            "length": 20.0,
            "width": 15.0,
            "height": 10.0,
            "max_weight": 5.0,
            "volume": 3000.0
        },
        {
            "box_id": "BOX-M",
            "name": "Medium Box",
            "length": 30.0,
            "width": 25.0,
            "height": 15.0,
            "max_weight": 10.0,
            "volume": 11250.0
        }
    ]
    
    mock_db_client.fetch_many.side_effect = [
        order_items_mock,
        boxes_mock
    ]
    
    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-TEST-001")
    
    assert result.success is True
    assert result.data["order_id"] == "ORD-TEST-001"
    assert result.data["total_volume_cm3"] == 300.0
    assert result.data["total_weight_kg"] == 3.0
    
    recs = result.data["recommendations"]
    assert len(recs) == 2
    assert recs[0]["box_id"] == "BOX-S"  # Small box should be more efficient (less wasted space) than medium box


@pytest.mark.asyncio
async def test_suggest_packing_box_not_found(mock_db_client, test_config):
    """Test when no items are found for the order"""
    mock_db_client.fetch_many.return_value = []
    
    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-EMPTY")
    
    assert result.success is False
    assert result.error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_suggest_packing_box_invalid_id(test_config):
    """Test with invalid order ID"""
    tool = SuggestPackingBox(test_config)
    
    result = await tool.execute(order_id="")
    
    assert result.success is False
    assert result.error_code == "VALIDATION_ERROR"
