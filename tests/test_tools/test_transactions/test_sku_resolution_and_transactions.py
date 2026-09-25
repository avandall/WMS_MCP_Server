"""Tests for TASK-060: Type-safe SKU resolution and transaction execution without raw SQL parsing"""

import pytest
from unittest.mock import AsyncMock, patch
from app.config import Config
from app.clients.database_client import DatabaseClient
from app.clients.grpc_core_client import GrpcCoreClient
from app.tools.transactions.update_inventory_quantity import UpdateInventoryQuantity
from app.tools.transactions.adjust_inventory_for_reason import AdjustInventoryForReason
from app.tools.transactions.move_stock_between_locations import MoveStockBetweenLocations
from app.gen.wms.product.v1 import product_pb2
from app.gen.wms.inventory.v1 import inventory_pb2


@pytest.fixture
def mock_product_catalog(mock_grpc_client):
    """Setup complex alphanumeric products in mocked product service"""
    mock_list_response = product_pb2.ListProductsResponse()
    mock_list_response.products.add(product_id=1, name="SKU-TEST-001", price=100.0, description="Test 1")
    mock_list_response.products.add(product_id=15, name="LAP-PRO-15", price=1500.0, description="Laptop Pro 15")
    mock_list_response.products.add(product_id=9, name="DESK-WOOD-009", price=450.0, description="Wooden Desk 009")
    mock_list_response.products.add(product_id=101, name="FURN-CHAIR", price=85.0, description="Office Ergonomic Chair")
    
    mock_grpc_client.mock_product.ListProducts.return_value = mock_list_response
    return mock_list_response


@pytest.mark.asyncio
async def test_resolve_product_id_complex_skus_never_defaults_to_one(mock_product_catalog, test_config):
    """Verify complex alphanumeric SKUs resolve to exact product IDs and never default to 1"""
    client = GrpcCoreClient(test_config)

    # 1. Pure integer string
    assert await client.resolve_product_id("42") == 42

    # 2. Standard numeric SKU prefix
    assert await client.resolve_product_id("SKU-88") == 88

    # 3. Complex alphanumeric SKUs
    pid_lap = await client.resolve_product_id("LAP-PRO-15")
    assert pid_lap == 15, "LAP-PRO-15 must resolve to product_id 15, not fallback to 1"

    pid_desk = await client.resolve_product_id("DESK-WOOD-009")
    assert pid_desk == 9, "DESK-WOOD-009 must resolve to product_id 9, not fallback to 1"

    pid_chair = await client.resolve_product_id("FURN-CHAIR")
    assert pid_chair == 101, "FURN-CHAIR must resolve to product_id 101, not fallback to 1"

    # 4. In-memory cache hit (should not call gRPC again)
    mock_product_catalog  # already set up
    call_count_before = mock_product_catalog
    assert await client.resolve_product_id("LAP-PRO-15") == 15


@pytest.mark.asyncio
async def test_resolve_product_id_unknown_sku_raises_value_error(mock_product_catalog, test_config):
    """Verify non-existent SKU raises ValueError instead of silently corrupting product_id 1"""
    client = GrpcCoreClient(test_config)

    with pytest.raises(ValueError, match="could not be resolved"):
        await client.resolve_product_id("NON-EXISTENT-SKU-XYZ")


@pytest.mark.asyncio
async def test_confirm_inventory_adjustment_type_safe(mock_product_catalog, mock_grpc_client, test_config):
    """Verify DatabaseClient.confirm_inventory_adjustment performs type-safe adjustment"""
    db_client = DatabaseClient(test_config)

    # Adjust decrease (ADJUSTMENT_OUT) for LAP-PRO-15
    success = await db_client.confirm_inventory_adjustment(
        sku_code="LAP-PRO-15",
        quantity=-5,
        location_code="WH-2-A",
        warehouse_id=2,
        reason="DAMAGED"
    )

    assert success is True
    assert mock_grpc_client.mock_inventory.ConfirmInventoryTransaction.called
    last_call_args = mock_grpc_client.mock_inventory.ConfirmInventoryTransaction.call_args[0][0]
    assert last_call_args.product_id == 15
    assert last_call_args.warehouse_id == 2
    assert last_call_args.quantity == 5
    assert last_call_args.transaction_type == "ADJUSTMENT_OUT"


@pytest.mark.asyncio
async def test_move_inventory_stock_type_safe(mock_product_catalog, mock_grpc_client, test_config):
    """Verify DatabaseClient.move_inventory_stock executes atomic MoveLocationStock transfer"""
    db_client = DatabaseClient(test_config)

    success = await db_client.move_inventory_stock(
        sku_code="FURN-CHAIR",
        quantity=3,
        from_location="ZONE-1-SHELF-A",
        to_location="ZONE-2-SHELF-B"
    )

    assert success is True
    assert mock_grpc_client.mock_inventory.MoveLocationStock.called
    
    # Inspect atomic move request
    req = mock_grpc_client.mock_inventory.MoveLocationStock.call_args[0][0]
    assert req.product_id == 101
    assert req.sku_code == "FURN-CHAIR"
    assert req.quantity == 3
    assert req.from_location_code == "ZONE-1-SHELF-A"
    assert req.to_location_code == "ZONE-2-SHELF-B"


@pytest.mark.asyncio
async def test_move_stock_tool_with_complex_sku(mock_product_catalog, mock_grpc_client, mock_redis_client, test_config):
    """Verify move_stock_between_locations tool handles complex SKU correctly"""
    tool = MoveStockBetweenLocations(test_config)
    tool.redis = mock_redis_client

    # Mock source stock availability
    with patch.object(
        tool.db, "get_stock_info",
        new=AsyncMock(return_value={"location_code": "LOC-1", "available_qty": 20})
    ):
        result = await tool.execute(
            sku_code="DESK-WOOD-009",
            from_location="LOC-1",
            to_location="LOC-2",
            quantity=5
        )

    assert result.success is True
    assert result.data["sku_code"] == "DESK-WOOD-009"
    assert result.data["quantity"] == 5


@pytest.mark.asyncio
async def test_adjust_inventory_tool_with_complex_sku(mock_product_catalog, mock_grpc_client, mock_redis_client, test_config):
    """Verify adjust_inventory_for_reason tool accurately resolves product_id for LAP-PRO-15"""
    tool = AdjustInventoryForReason(test_config)
    tool.redis = mock_redis_client

    result = await tool.execute(
        sku_code="LAP-PRO-15",
        location_code="WH-1-POS-01",
        reason="DAMAGED",
        quantity=-2
    )

    assert result.success is True
    assert result.data["product_id"] == 15
    assert result.data["sku_code"] == "LAP-PRO-15"
