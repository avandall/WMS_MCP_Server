"""Unit tests for audit_user_permissions tool"""

import pytest
from app.tools.users.audit_user_permissions import AuditUserPermissions
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_audit_user_permissions_success(mock_db_client, test_config):
    """Test successful permission audit check"""
    user_mock = {
        "user_id": "USR-001",
        "username": "manager_bob",
        "role": "MANAGER",
        "status": "ACTIVE",
        "warehouse_access": [1, 2]
    }
    
    direct_perms_mock = [
        {"permission": "READ_STOCK"}
    ]
    
    role_perms_mock = [
        {"permission": "UPDATE_STOCK"},
        {"permission": "DELETE_STOCK"}
    ]
    
    mock_db_client.fetch_one.return_value = user_mock
    mock_db_client.fetch_many.side_effect = [
        direct_perms_mock,
        role_perms_mock
    ]
    
    tool = AuditUserPermissions(test_config)
    tool.db = mock_db_client
    
    # BOB has DELETE_STOCK (critical) through role permissions
    result = await tool.execute(user_id="USR-001", action_required="DELETE_STOCK")
    
    assert result.success is True
    assert result.data["user_id"] == "USR-001"
    assert result.data["username"] == "manager_bob"
    assert result.data["role"] == "MANAGER"
    assert result.data["has_permission"] is True
    assert "DELETE_STOCK" in result.data["all_permissions"]
    assert "critical action" in result.data["recommendation"].lower()


@pytest.mark.asyncio
async def test_audit_user_permissions_denied(mock_db_client, test_config):
    """Test permission audit check when permission is denied"""
    user_mock = {
        "user_id": "USR-002",
        "username": "picker_alice",
        "role": "PICKER",
        "status": "ACTIVE",
        "warehouse_access": [1]
    }
    
    direct_perms_mock = [
        {"permission": "READ_STOCK"}
    ]
    
    role_perms_mock = [
        {"permission": "MOVE_STOCK"}
    ]
    
    mock_db_client.fetch_one.return_value = user_mock
    mock_db_client.fetch_many.side_effect = [
        direct_perms_mock,
        role_perms_mock
    ]
    
    tool = AuditUserPermissions(test_config)
    tool.db = mock_db_client
    
    # Alice requests DELETE_STOCK (critical) but doesn't have it
    result = await tool.execute(user_id="USR-002", action_required="DELETE_STOCK")
    
    assert result.success is True
    assert result.data["has_permission"] is False
    assert "action denied" in result.data["recommendation"].lower()
    assert "HIGH_RISK_ACTION_BLOCKED" in result.data["security_assessment"]["security_flags"]


@pytest.mark.asyncio
async def test_audit_user_permissions_user_not_found(mock_db_client, test_config):
    """Test permission audit check when user is not found"""
    mock_db_client.fetch_one.return_value = None
    
    tool = AuditUserPermissions(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(user_id="USR-NOT-FOUND", action_required="READ_STOCK")
    
    assert result.success is False
    assert result.error_code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_audit_user_permissions_invalid_id(test_config):
    """Test permission audit check with invalid user ID"""
    tool = AuditUserPermissions(test_config)
    
    result = await tool.execute(user_id="", action_required="READ_STOCK")
    
    assert result.success is False
    assert result.error_code == "VALIDATION_ERROR"
