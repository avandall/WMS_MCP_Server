"""Unit tests for get_order_status_details tool"""

import pytest
from app.tools.orders.get_order_status_details import GetOrderStatusDetails
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_get_order_status_details_success(mock_db_client, test_config, sample_order_data):
    """Test successful order status details lookup"""
    mock_db_client.fetch_one.return_value = {
        "order_id": "ORD-TEST-001",
        "customer_id": "CUST-001",
        "customer_name": "Test Customer",
        "status": "CONFIRMED",
        "order_date": "2024-01-01T00:00:00Z",
        "total_amount": 1000.00,
        "shipping_address": "123 Main St",
        "billing_address": "123 Main St",
        "priority": "NORMAL",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
    
    mock_db_client.fetch_many.return_value = [
        {
            "item_id": 1,
            "sku_code": "SKU-TEST-001",
            "quantity": 10,
            "unit_price": 100.00,
            "total_price": 1000.00,
            "item_status": "PENDING"
        }
    ]
    
    tool = GetOrderStatusDetails(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-TEST-001")
    
    assert result.success is True
    assert result.data["order_info"]["order_id"] == "ORD-TEST-001"
    assert result.data["total_quantity"] == 10
    assert result.data["total_items"] == 1
    
    summary = result.data["summary"]
    assert summary["customer"] == "Test Customer"
    assert summary["ready_for_next_stage"] is True


@pytest.mark.asyncio
async def test_get_order_status_details_not_found(mock_db_client, test_config):
    """Test order status lookup when order is not found"""
    mock_db_client.fetch_one.return_value = None
    
    tool = GetOrderStatusDetails(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-NOT-FOUND")
    
    assert result.success is False
    assert result.error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_order_status_details_invalid_id(test_config):
    """Test order status lookup with invalid order ID"""
    tool = GetOrderStatusDetails(test_config)
    
    result = await tool.execute(order_id="")
    
    assert result.success is False
    assert result.error_code == "VALIDATION_ERROR"
