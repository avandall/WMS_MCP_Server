"""Unit tests for get_low_stock_report tool"""

import pytest
from app.tools.alerts.get_low_stock_report import GetLowStockReport, GetLowStockReportInput
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_get_low_stock_report_no_items(mock_db_client, test_config):
    """Test when no items are low stock"""
    mock_db_client.fetch_many.return_value = []
    
    tool = GetLowStockReport(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute()
    
    assert result.success is True
    assert result.data["total_items"] == 0
    assert "No items found" in result.data["message"]


@pytest.mark.asyncio
async def test_get_low_stock_report_with_items(mock_db_client, test_config):
    """Test when items are low stock"""
    low_stock_data = [
        {
            "sku_code": "SKU-TEST-001",
            "warehouse_id": 1,
            "available_qty": 0,
            "safety_stock": 10
        },
        {
            "sku_code": "SKU-TEST-002",
            "warehouse_id": 2,
            "available_qty": 5,
            "safety_stock": 15
        }
    ]
    mock_db_client.fetch_many.return_value = low_stock_data
    
    tool = GetLowStockReport(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(threshold_qty=20)
    
    assert result.success is True
    assert result.data["total_items"] == 2
    assert len(result.data["low_stock_items"]) == 2
    assert result.data["threshold_used"] == 20
    
    analysis = result.data["analysis"]
    assert analysis["critical_count"] == 1  # SKU-TEST-001 has available_qty == 0
    assert analysis["warning_count"] == 1
    assert 1 in analysis["warehouses_affected"]
    assert 2 in analysis["warehouses_affected"]
    assert "URGENT" in analysis["recommendation"]


@pytest.mark.asyncio
async def test_get_low_stock_report_invalid_threshold(test_config):
    """Test with invalid custom threshold"""
    tool = GetLowStockReport(test_config)
    
    result = await tool.execute(threshold_qty=-5)
    
    assert result.success is False
    assert result.error_code == "VALIDATION_ERROR"
