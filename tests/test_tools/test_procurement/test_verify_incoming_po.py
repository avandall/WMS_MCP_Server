"""Unit tests for verify_incoming_po tool"""

import pytest
from app.tools.procurement.verify_incoming_po import VerifyIncomingPO
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_verify_incoming_po_match(mock_db_client, test_config):
    """Test verification when received items match PO exactly"""
    po_info_mock = {
        "po_number": "PO-TEST-001",
        "supplier_id": "SUPP-001",
        "supplier_name": "Test Supplier",
        "expected_date": "2024-01-01",
        "status": "PENDING"
    }
    
    po_items_mock = [
        {
            "sku_code": "SKU-TEST-001",
            "ordered_quantity": 100,
            "unit_price": 5.0,
            "received_quantity": 0
        }
    ]
    
    mock_db_client.fetch_one.return_value = po_info_mock
    mock_db_client.fetch_many.return_value = po_items_mock
    
    tool = VerifyIncomingPO(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(
        po_number="PO-TEST-001",
        received_items=[
            {"sku_code": "SKU-TEST-001", "quantity": 100}
        ]
    )
    
    assert result.success is True
    assert result.data["overall_status"] == "MATCH"
    assert result.data["requires_action"] is False
    assert "matches PO exactly" in result.data["recommendations"][0]


@pytest.mark.asyncio
async def test_verify_incoming_po_shortage(mock_db_client, test_config):
    """Test verification when there is a shortage"""
    po_info_mock = {
        "po_number": "PO-TEST-001",
        "supplier_id": "SUPP-001",
        "supplier_name": "Test Supplier",
        "expected_date": "2024-01-01",
        "status": "PENDING"
    }
    
    po_items_mock = [
        {
            "sku_code": "SKU-TEST-001",
            "ordered_quantity": 100,
            "unit_price": 5.0,
            "received_quantity": 0
        }
    ]
    
    mock_db_client.fetch_one.return_value = po_info_mock
    mock_db_client.fetch_many.return_value = po_items_mock
    
    tool = VerifyIncomingPO(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(
        po_number="PO-TEST-001",
        received_items=[
            {"sku_code": "SKU-TEST-001", "quantity": 80}
        ]
    )
    
    assert result.success is True
    assert result.data["overall_status"] == "DISCREPANCY"
    assert result.data["requires_action"] is True
    assert len(result.data["verification_result"]["discrepancies"]) == 1
    disc = result.data["verification_result"]["discrepancies"][0]
    assert disc["type"] == "SHORTAGE"
    assert disc["difference"] == -20
    assert "missing" in result.data["recommendations"][0]


@pytest.mark.asyncio
async def test_verify_incoming_po_not_found(mock_db_client, test_config):
    """Test verification when purchase order is not found"""
    mock_db_client.fetch_one.return_value = None
    
    tool = VerifyIncomingPO(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(
        po_number="PO-NOT-FOUND",
        received_items=[]
    )
    
    assert result.success is False
    assert result.error_code == "NOT_FOUND"
