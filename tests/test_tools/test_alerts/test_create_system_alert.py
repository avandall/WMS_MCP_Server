"""Unit tests for create_system_alert tool"""

import pytest
from app.tools.alerts.create_system_alert import CreateSystemAlert
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_create_system_alert_success(mock_db_client, test_config):
    """Test successful system alert creation"""
    tool = CreateSystemAlert(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(
        alert_type="CRITICAL",
        message="Warehouse A is at 98% volume capacity",
        source="volume_monitor",
        details={"current_volume": 9800.0, "max_volume": 10000.0}
    )
    
    assert result.success is True
    assert result.data["alert_type"] == "CRITICAL"
    assert result.data["message"] == "Warehouse A is at 98% volume capacity"
    assert result.data["source"] == "volume_monitor"
    assert result.data["needs_notification"] is True
    assert mock_db_client.execute.called


@pytest.mark.asyncio
async def test_create_system_alert_warning_success(mock_db_client, test_config):
    """Test successful warning system alert creation"""
    tool = CreateSystemAlert(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(
        alert_type="WARNING",
        message="Slight temperature variation in Zone B",
        source="temp_sensor_2"
    )
    
    assert result.success is True
    assert result.data["alert_type"] == "WARNING"
    assert result.data["needs_notification"] is False
    assert mock_db_client.execute.called


@pytest.mark.asyncio
async def test_create_system_alert_invalid_type(test_config):
    """Test with invalid alert type"""
    tool = CreateSystemAlert(test_config)
    
    result = await tool.execute(
        alert_type="INVALID_TYPE",
        message="This should fail"
    )
    
    assert result.success is False
    assert result.error_code == "VALIDATION_ERROR"
