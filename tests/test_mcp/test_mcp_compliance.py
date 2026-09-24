"""MCP specification compliance & Fault Tolerance tests for TASK-043"""

import pytest
from unittest.mock import AsyncMock
from app.config import Config
from app.tools.registry import ToolRegistry
from app.tools.base import ToolResult
from app.clients.grpc_core_client import GrpcCoreClient
from app.clients.database_client import DatabaseClient
from app.tools.transactions.move_stock_between_locations import MoveStockBetweenLocations
from app.exceptions import UpstreamServiceUnavailableError


@pytest.mark.mcp
class TestMCPCompliance:
    """MCP specification compliance tests"""

    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test that all tools are properly registered"""
        from app.server import register_tools_from_categories, registry
        await register_tools_from_categories()
        tools = registry.list_tools()
        assert len(tools) > 0
        tool_names = [t["name"] for t in tools]
        assert "check_stock_availability" in tool_names
        assert "move_stock_between_locations" in tool_names
        assert "update_inventory_quantity" in tool_names

    @pytest.mark.asyncio
    async def test_tool_schema_validation(self):
        """Test that tool schemas are valid"""
        from app.server import register_tools_from_categories, registry
        await register_tools_from_categories()
        for tool in registry.list_tools():
            schema = tool["input_schema"]
            assert isinstance(schema, dict)
            assert schema.get("type") == "object"
            assert "properties" in schema

    @pytest.mark.asyncio
    async def test_tool_response_format(self):
        """Test that tool responses follow MCP format"""
        res = ToolResult(success=True, data={"test": 123})
        assert res.success is True
        assert res.data == {"test": 123}
        assert res.error is None

    @pytest.mark.asyncio
    async def test_error_handling_compliance(self):
        """Test that error handling follows MCP spec with standardized ToolResult"""
        res = ToolResult(success=False, error="Service failure", error_code="UPSTREAM_UNAVAILABLE")
        assert res.success is False
        assert res.error_code == "UPSTREAM_UNAVAILABLE"


@pytest.mark.asyncio
async def test_grpc_core_down_raises_upstream_unavailable(mock_grpc_client, test_config):
    """
    TASK-043 [AI-FATAL-01]: When gRPC Core is down, GrpcCoreClient MUST raise
    UpstreamServiceUnavailableError and NEVER return phantom stock numbers (100, 10, 90).
    """
    mock_grpc_client.mock_inventory.GetAvailability.side_effect = Exception("Connection refused: 50051")
    client = GrpcCoreClient(test_config)

    with pytest.raises(UpstreamServiceUnavailableError) as exc_info:
        await client.get_stock_info(sku_or_id="SKU-TEST-001", warehouse_id=1)

    assert "Inventory Service unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_grpc_locations_and_docs_raise_upstream_unavailable(mock_grpc_client, test_config):
    """
    TASK-043 [AI-FATAL-01]: When gRPC Core fails, get_inventory_locations, get_document,
    and get_product MUST raise UpstreamServiceUnavailableError instead of returning mock fallback data.
    """
    mock_grpc_client.mock_inventory.GetInventoryLocations.side_effect = Exception("Core down")
    mock_grpc_client.mock_documents.GetDocument.side_effect = Exception("Core down")
    mock_grpc_client.mock_product.GetProduct.side_effect = Exception("Core down")
    client = GrpcCoreClient(test_config)

    with pytest.raises(UpstreamServiceUnavailableError):
        await client.get_inventory_locations(warehouse_id=1)

    with pytest.raises(UpstreamServiceUnavailableError):
        await client.get_document(document_id=1)

    with pytest.raises(UpstreamServiceUnavailableError):
        await client.get_product(product_id=1)


@pytest.mark.asyncio
async def test_move_stock_tool_fails_cleanly_when_core_is_down(mock_grpc_client, test_config):
    """
    TASK-043: If WMS Core is down, MoveStockBetweenLocations MUST fail cleanly with
    error_code='UPSTREAM_UNAVAILABLE' and NEVER report phantom success.
    """
    mock_grpc_client.mock_inventory.GetAvailability.side_effect = Exception("Connection refused: Core down")
    tool = MoveStockBetweenLocations(test_config)

    result = await tool.execute(
        sku_code="SKU-TEST-001",
        from_location="ZONE-A-ROW-01-SHELF-01",
        to_location="ZONE-A-ROW-02-SHELF-02",
        quantity=5
    )

    assert result.success is False
    assert result.error_code == "UPSTREAM_UNAVAILABLE"
    assert "unavailable" in result.error.lower()


@pytest.mark.asyncio
async def test_database_client_delegates_to_grpc_not_stubs(mock_grpc_client, test_config):
    """
    TASK-043 [AI-FATAL-02]: DatabaseClient.update_stock_quantity and execute_transaction
    must call WMS Core gRPC and propagate errors, never returning dummy True.
    """
    # 1. When Core is UP: calls ConfirmInventoryTransaction
    from app.gen.wms.inventory.v1 import inventory_pb2
    mock_grpc_client.mock_inventory.ConfirmInventoryTransaction.return_value = (
        inventory_pb2.ConfirmInventoryTransactionResponse(success=True, transaction_id=999)
    )
    db = DatabaseClient(test_config)
    ok = await db.update_stock_quantity(
        sku_code="SKU-001",
        location_code="ZONE-A-01",
        quantity=10,
        warehouse_id=1
    )
    assert ok is True
    assert mock_grpc_client.mock_inventory.ConfirmInventoryTransaction.called

    # 2. When Core is DOWN: must raise UpstreamServiceUnavailableError, NOT return True
    mock_grpc_client.mock_inventory.ConfirmInventoryTransaction.side_effect = Exception("Core down")
    with pytest.raises(UpstreamServiceUnavailableError):
        await db.update_stock_quantity(
            sku_code="SKU-001",
            location_code="ZONE-A-01",
            quantity=10,
            warehouse_id=1
        )

    with pytest.raises(UpstreamServiceUnavailableError):
        await db.execute_transaction([
            {
                "query": "UPDATE inventory_stock SET physical_qty = physical_qty - $1 WHERE sku_code = $2 AND location_code = $3",
                "params": [5, "SKU-001", "ZONE-A-01"]
            }
        ])
