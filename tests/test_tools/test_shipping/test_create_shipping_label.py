"""Unit tests for create_shipping_label tool"""

import pytest
from app.tools.shipping.create_shipping_label import CreateShippingLabel
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_create_shipping_label_success(mock_db_client, test_config):
    """Test successful shipping label creation"""
    order_mock = {
        "order_id": "ORD-TEST-001",
        "customer_id": "CUST-001",
        "customer_name": "Test Customer",
        "customer_phone": "1234567890",
        "shipping_address": "123 Main St",
        "shipping_city": "Hanoi",
        "shipping_postal_code": "100000",
        "total_weight_kg": 2.5,
        "total_volume_cm3": 1200.0,
        "status": "PACKED"
    }
    
    carrier_mock = {
        "carrier_id": "GHTK",
        "carrier_name": "Giao Hang Tiet Kiem",
        "api_endpoint": "https://api.ghtk.vn",
        "requires_auth": True
    }
    
    mock_db_client.fetch_one.side_effect = [
        order_mock,
        carrier_mock
    ]
    
    tool = CreateShippingLabel(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-TEST-001", carrier_id="GHTK")
    
    assert result.success is True
    assert result.data["order_id"] == "ORD-TEST-001"
    assert result.data["carrier_id"] == "GHTK"
    assert "tracking_number" in result.data
    assert "label_url" in result.data
    assert mock_db_client.execute.called


@pytest.mark.asyncio
async def test_create_shipping_label_invalid_status(mock_db_client, test_config):
    """Test when order is not yet packed / ready to ship"""
    order_mock = {
        "order_id": "ORD-TEST-001",
        "status": "PENDING"
    }
    
    mock_db_client.fetch_one.return_value = order_mock
    
    tool = CreateShippingLabel(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-TEST-001", carrier_id="GHTK")
    
    assert result.success is False
    assert result.error_code == "INVALID_STATUS"


@pytest.mark.asyncio
async def test_create_shipping_label_order_not_found(mock_db_client, test_config):
    """Test when order is not found"""
    mock_db_client.fetch_one.return_value = None
    
    tool = CreateShippingLabel(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-NOT-FOUND", carrier_id="GHTK")
    
    assert result.success is False
    assert result.error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_shipping_label_carrier_not_found(mock_db_client, test_config):
    """Test when carrier is not found"""
    order_mock = {
        "order_id": "ORD-TEST-001",
        "status": "PACKED"
    }
    
    mock_db_client.fetch_one.side_effect = [
        order_mock,
        None
    ]
    
    tool = CreateShippingLabel(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-TEST-001", carrier_id="INVALID_CARRIER")
    
    assert result.success is False
    assert result.error_code == "NOT_FOUND"
