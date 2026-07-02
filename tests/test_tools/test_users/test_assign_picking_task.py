"""Unit tests for assign_picking_task tool"""

import pytest
from app.tools.users.assign_picking_task import AssignPickingTask
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_assign_picking_task_success(mock_db_client, test_config):
    """Test successful task assignment"""
    user_mock = {
        "user_id": "USR-001",
        "username": "picker_john",
        "status": "AVAILABLE",
        "current_task_id": None
    }
    
    task_mock = {
        "task_id": "TSK-001",
        "task_type": "PICKING",
        "status": "UNASSIGNED",
        "order_id": "ORD-001",
        "priority": "HIGH"
    }
    
    mock_db_client.fetch_one.side_effect = [
        user_mock,
        task_mock
    ]
    
    tool = AssignPickingTask(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(task_id="TSK-001", user_id="USR-001")
    
    assert result.success is True
    assert result.data["task_id"] == "TSK-001"
    assert result.data["user_id"] == "USR-001"
    assert result.data["username"] == "picker_john"
    assert result.data["priority"] == "HIGH"
    assert mock_db_client.execute_transaction.called


@pytest.mark.asyncio
async def test_assign_picking_task_user_not_found(mock_db_client, test_config):
    """Test task assignment when user does not exist"""
    mock_db_client.fetch_one.return_value = None
    
    tool = AssignPickingTask(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(task_id="TSK-001", user_id="USR-NOT-FOUND")
    
    assert result.success is False
    assert result.error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_assign_picking_task_user_busy(mock_db_client, test_config):
    """Test task assignment when user is busy"""
    user_mock = {
        "user_id": "USR-001",
        "username": "picker_john",
        "status": "BUSY",
        "current_task_id": "TSK-OLD"
    }
    mock_db_client.fetch_one.return_value = user_mock
    
    tool = AssignPickingTask(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(task_id="TSK-001", user_id="USR-001")
    
    assert result.success is False
    assert result.error_code == "USER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_assign_picking_task_task_not_found(mock_db_client, test_config):
    """Test task assignment when task does not exist"""
    user_mock = {
        "user_id": "USR-001",
        "username": "picker_john",
        "status": "AVAILABLE",
        "current_task_id": None
    }
    mock_db_client.fetch_one.side_effect = [
        user_mock,
        None
    ]
    
    tool = AssignPickingTask(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(task_id="TSK-NOT-FOUND", user_id="USR-001")
    
    assert result.success is False
    assert result.error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_assign_picking_task_task_already_assigned(mock_db_client, test_config):
    """Test task assignment when task is already assigned"""
    user_mock = {
        "user_id": "USR-001",
        "username": "picker_john",
        "status": "AVAILABLE",
        "current_task_id": None
    }
    
    task_mock = {
        "task_id": "TSK-001",
        "task_type": "PICKING",
        "status": "ASSIGNED",
        "order_id": "ORD-001",
        "priority": "HIGH"
    }
    
    mock_db_client.fetch_one.side_effect = [
        user_mock,
        task_mock
    ]
    
    tool = AssignPickingTask(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(task_id="TSK-001", user_id="USR-001")
    
    assert result.success is False
    assert result.error_code == "TASK_UNAVAILABLE"
