"""Tests for WMS MCP Server Draft Proposal Tools (TASK-075: CRIT-03 & CRIT-04)

Verifies:
1. UpdateInventoryQuantity and AdjustInventoryForReason invoke CreateDraftProposal (Maker-Checker workflow).
2. Direct stock mutation via ConfirmInventoryTransaction is NEVER called by these tools.
3. Explicit warehouse_id is passed and preserved; regex digits parsing is eliminated so location codes
   like AISLE-12-BAY-03 or ZONE-99 do not corrupt warehouse_id.
4. Status DRAFT_PROPOSAL is returned in tool results.
"""

import pytest
from unittest.mock import AsyncMock
from app.tools.transactions.update_inventory_quantity import UpdateInventoryQuantity, UpdateInventoryQuantityInput
from app.tools.transactions.adjust_inventory_for_reason import AdjustInventoryForReason, AdjustInventoryForReasonInput
from app.clients.grpc_core_client import GrpcCoreClient
from app.gen.wms.inventory.v1 import inventory_pb2


@pytest.mark.asyncio
async def test_update_inventory_quantity_creates_draft_proposal(mock_grpc_client, mock_redis_client, test_config):
    """Verify update_inventory_quantity creates a draft proposal and NEVER mutates stock directly"""
    mock_redis_client.acquire_lock.return_value = True
    mock_redis_client.release_lock.return_value = True
    mock_redis_client.cache_delete.return_value = True

    tool = UpdateInventoryQuantity(test_config)
    tool.redis = mock_redis_client

    # Execute INCREASE in Warehouse 1 with location code containing number 12 (CRIT-04 regex regression test)
    result = await tool.execute(
        sku_code="SKU-TEST-001",
        location_code="AISLE-12-BAY-03",
        action="INCREASE",
        quantity=25,
        warehouse_id=1
    )

    # 1. Tool execution must succeed with DRAFT_PROPOSAL status
    assert result.success is True
    assert result.data["status"] == "DRAFT_PROPOSAL"
    assert result.data["action"] == "INCREASE"
    assert result.data["quantity"] == 25
    assert result.data["adjustment"] == 25
    assert result.data["warehouse_id"] == 1
    assert result.data["location_code"] == "AISLE-12-BAY-03"

    # 2. ConfirmInventoryTransaction must NOT be called (CRIT-03: Maker-Checker compliance)
    assert not mock_grpc_client.mock_inventory.ConfirmInventoryTransaction.called, (
        "ConfirmInventoryTransaction should NEVER be called directly by AI agent update tool!"
    )

    # 3. CreateDraftProposal must be called with explicit warehouse_id=1 (NOT 12 from regex)
    assert mock_grpc_client.mock_inventory.CreateDraftProposal.called
    call_args = mock_grpc_client.mock_inventory.CreateDraftProposal.call_args[0][0]
    assert call_args.warehouse_id == 1, f"warehouse_id must be 1, but got {call_args.warehouse_id}"
    assert call_args.sku_code == "SKU-TEST-001"
    assert call_args.location_code == "AISLE-12-BAY-03"
    assert call_args.adjustment == 25
    assert call_args.requested_by == "mcp-agent"


@pytest.mark.asyncio
async def test_update_inventory_quantity_decrease_creates_negative_adjustment(mock_grpc_client, mock_redis_client, test_config):
    """Verify DECREASE action creates draft proposal with negative adjustment"""
    mock_redis_client.acquire_lock.return_value = True
    mock_redis_client.release_lock.return_value = True

    tool = UpdateInventoryQuantity(test_config)
    tool.redis = mock_redis_client

    result = await tool.execute(
        sku_code="SKU-TEST-001",
        location_code="BIN-42",
        action="DECREASE",
        quantity=15,
        warehouse_id=2
    )

    assert result.success is True
    assert result.data["status"] == "DRAFT_PROPOSAL"
    assert result.data["adjustment"] == -15
    assert result.data["warehouse_id"] == 2

    # Verify gRPC request parameters
    assert not mock_grpc_client.mock_inventory.ConfirmInventoryTransaction.called
    call_args = mock_grpc_client.mock_inventory.CreateDraftProposal.call_args[0][0]
    assert call_args.warehouse_id == 2
    assert call_args.adjustment == -15
    assert call_args.location_code == "BIN-42"


@pytest.mark.asyncio
async def test_adjust_inventory_for_reason_creates_draft_proposal(mock_grpc_client, mock_redis_client, test_config):
    """Verify adjust_inventory_for_reason creates draft proposal and preserves explicit warehouse_id"""
    mock_redis_client.acquire_lock.return_value = True
    mock_redis_client.release_lock.return_value = True

    tool = AdjustInventoryForReason(test_config)
    tool.redis = mock_redis_client

    # Location code has number 99, but explicit warehouse_id is 3
    result = await tool.execute(
        sku_code="SKU-TEST-001",
        location_code="AISLE-99-BAY-05",
        reason="DAMAGED",
        quantity=-7,
        warehouse_id=3
    )

    assert result.success is True
    assert result.data["status"] == "DRAFT_PROPOSAL"
    assert result.data["reason"] == "DAMAGED"
    assert result.data["quantity"] == -7
    assert result.data["adjustment"] == -7
    assert result.data["warehouse_id"] == 3

    # Direct mutation must NOT occur
    assert not mock_grpc_client.mock_inventory.ConfirmInventoryTransaction.called

    # Proposal creation must receive warehouse_id=3 (not 99)
    call_args = mock_grpc_client.mock_inventory.CreateDraftProposal.call_args[0][0]
    assert call_args.warehouse_id == 3, f"Expected warehouse_id 3, got {call_args.warehouse_id}"
    assert call_args.adjustment == -7
    assert call_args.reason == "DAMAGED"
    assert call_args.location_code == "AISLE-99-BAY-05"
    assert call_args.requested_by == "mcp-agent"


@pytest.mark.asyncio
async def test_grpc_core_client_create_draft_proposal_method(mock_grpc_client, test_config):
    """Verify GrpcCoreClient.create_draft_proposal correctly maps protobuf response"""
    client = GrpcCoreClient(test_config)

    proposal = await client.create_draft_proposal(
        sku_code="SKU-TEST-001",
        warehouse_id=2,
        location_code="ZONE-B-ROW-01",
        adjustment=-10,
        reason="EXPIRED",
        proposal_type="REASON_ADJUSTMENT",
        requested_by="mcp-agent"
    )

    assert proposal["proposal_id"] == "PROP-TEST-001"
    assert proposal["status"] == "DRAFT_PROPOSAL"
    assert proposal["warehouse_id"] == 1  # returned from mock response
    assert proposal["sku_code"] == "SKU-TEST-001"


@pytest.mark.asyncio
async def test_proposal_tool_handles_core_service_failure(mock_grpc_client, mock_redis_client, test_config):
    """Verify tool handles upstream gRPC service failure gracefully"""
    mock_redis_client.acquire_lock.return_value = True
    mock_redis_client.release_lock.return_value = True

    # Override mock to return failure
    fail_response = inventory_pb2.CreateDraftProposalResponse(
        success=False,
        message="Negative adjustment requires non-empty location_code"
    )
    mock_grpc_client.mock_inventory.CreateDraftProposal.return_value = fail_response

    tool = UpdateInventoryQuantity(test_config)
    tool.redis = mock_redis_client

    result = await tool.execute(
        sku_code="SKU-TEST-001",
        location_code="LOC-1",
        action="DECREASE",
        quantity=5
    )

    assert result.success is False
    assert result.error_code == "PROPOSAL_CREATION_FAILED"
    assert "location_code" in result.error
    assert mock_redis_client.release_lock.called
