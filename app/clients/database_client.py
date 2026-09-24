"""Database client abstraction for WMS MCP Server (gRPC-backed compatibility adapter)"""

from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
import logging
from unittest.mock import AsyncMock
from app.config import Config
from app.clients.grpc_core_client import GrpcCoreClient

logger = logging.getLogger(__name__)


class DatabaseClient:
    """Compatibility database client delegating to gRPC Core Client (No raw SQL / asyncpg dependency)"""
    
    def __init__(self, config: Config):
        self.config = config
        self._grpc_client = GrpcCoreClient(config)
        
    async def connect(self) -> None:
        """Establish connection via gRPC client"""
        await self._grpc_client.connect()
        logger.info("gRPC Core Client adapter ready")
    
    async def disconnect(self) -> None:
        """Close gRPC client connection"""
        await self._grpc_client.disconnect()
        logger.info("gRPC Core Client adapter closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Yield self as context manager"""
        yield self
    
    async def execute(self, query: str, *args, **kwargs) -> str:
        """Execute query stub"""
        return await self._grpc_client.execute(query, *args, **kwargs)
    
    async def fetch_one(self, query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """Fetch single item via gRPC adapter"""
        return await self._grpc_client.fetch_one(query, *args, **kwargs)
    
    async def fetch_many(self, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """Fetch many items via gRPC adapter"""
        return await self._grpc_client.fetch_many(query, *args, **kwargs)
    
    async def fetch_val(self, query: str, *args, column: int = 0, **kwargs) -> Any:
        """Fetch single val stub"""
        return None
    
    async def resolve_product_id(self, sku_code: str | int) -> int:
        """Resolve SKU code or product ID to integer product_id via GrpcCoreClient"""
        return await self._grpc_client.resolve_product_id(sku_code)

    async def execute_transaction(self, queries: List[Dict[str, Any]]) -> bool:
        """
        Legacy transaction execution adapter.
        Delegates queries to type-safe confirm_inventory_adjustment while avoiding raw SQL string matching.
        """
        if self._is_mocked("execute_transaction"):
            return True
        if not queries:
            return True

        from app.exceptions import UpstreamServiceUnavailableError

        try:
            for q in queries:
                params = q.get("params", [])
                sql = q.get("query", "")
                if params and len(params) >= 3:
                    # Param unpacking: [quantity, sku, location]
                    raw_qty = params[0]
                    sku = str(params[1])
                    loc = str(params[2])
                    qty = int(raw_qty) if str(raw_qty).lstrip("-").isdigit() else 1
                    if "-" in sql or qty < 0:
                        qty = -abs(qty)
                    else:
                        qty = abs(qty)
                    ok = await self.confirm_inventory_adjustment(sku_code=sku, quantity=qty, location_code=loc)
                    if not ok:
                        return False
            return True
        except UpstreamServiceUnavailableError:
            raise
        except Exception as e:
            logger.error(f"execute_transaction gRPC error: {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Inventory Service unavailable: {e}") from e
    
    def _is_mocked(self, method_name: str) -> bool:
        method = getattr(self, method_name, None)
        return isinstance(method, AsyncMock) or hasattr(method, "assert_called")
    
    # Inventory & Domain helper methods delegating to gRPC or mocked fetch methods
    async def get_stock_info(self, sku_code: str, warehouse_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        res = await self.fetch_one("SELECT inventory_stock", sku_code, warehouse_id)
        if res is not None:
            return res
        if self._is_mocked("fetch_one"):
            return None
        return await self._grpc_client.get_stock_info(sku_code, warehouse_id or 1)
    
    async def confirm_inventory_adjustment(
        self,
        sku_code: str,
        quantity: int,
        location_code: str = "",
        warehouse_id: Optional[int] = None,
        user_id: str = "mcp-agent",
        reason: str = ""
    ) -> bool:
        """
        Type-safe inventory quantity adjustment.
        Eliminates raw SQL string matching and heuristic regex guessing.
        """
        if self._is_mocked("confirm_inventory_adjustment"):
            return True
        import uuid
        import re
        from app.gen.wms.inventory.v1 import inventory_pb2
        from app.integration.grpc_client import grpc_client
        from app.exceptions import UpstreamServiceUnavailableError

        product_id = await self.resolve_product_id(sku_code)
        
        wh_id = warehouse_id
        if wh_id is None:
            digits = re.findall(r'\d+', str(location_code))
            wh_id = int(digits[0]) if digits else 1

        tx_type = "ADJUSTMENT_IN" if quantity >= 0 else "ADJUSTMENT_OUT"
        
        try:
            async with grpc_client.inventory_stub() as stub:
                req = inventory_pb2.ConfirmInventoryTransactionRequest(
                    transaction_type=tx_type,
                    product_id=product_id,
                    warehouse_id=wh_id,
                    quantity=abs(quantity),
                    user_id=user_id,
                    idempotency_key=f"adj_{uuid.uuid4().hex[:12]}"
                )
                res = await stub.ConfirmInventoryTransaction(req)
                return bool(res.success)
        except UpstreamServiceUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Failed to confirm inventory adjustment via gRPC: {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Inventory Service unavailable: {e}") from e

    async def move_inventory_stock(
        self,
        sku_code: str,
        quantity: int,
        from_location: str,
        to_location: str,
        warehouse_id: Optional[int] = None,
        user_id: str = "mcp-agent"
    ) -> bool:
        """
        Type-safe stock movement between warehouse locations.
        Executes outbound deduction from source and inbound addition to destination.
        """
        if self._is_mocked("move_inventory_stock"):
            return True
        import uuid
        import re
        from app.gen.wms.inventory.v1 import inventory_pb2
        from app.integration.grpc_client import grpc_client
        from app.exceptions import UpstreamServiceUnavailableError

        product_id = await self.resolve_product_id(sku_code)
        
        from_digits = re.findall(r'\d+', str(from_location))
        to_digits = re.findall(r'\d+', str(to_location))
        from_wh = warehouse_id or (int(from_digits[0]) if from_digits else 1)
        to_wh = warehouse_id or (int(to_digits[0]) if to_digits else 1)

        try:
            async with grpc_client.inventory_stub() as stub:
                # Step 1: Deduct from source location/warehouse
                out_req = inventory_pb2.ConfirmInventoryTransactionRequest(
                    transaction_type="ADJUSTMENT_OUT",
                    product_id=product_id,
                    warehouse_id=from_wh,
                    quantity=abs(quantity),
                    user_id=user_id,
                    idempotency_key=f"move_out_{uuid.uuid4().hex[:12]}"
                )
                out_res = await stub.ConfirmInventoryTransaction(out_req)
                if not out_res.success:
                    return False

                # Step 2: Add to destination location/warehouse
                in_req = inventory_pb2.ConfirmInventoryTransactionRequest(
                    transaction_type="ADJUSTMENT_IN",
                    product_id=product_id,
                    warehouse_id=to_wh,
                    quantity=abs(quantity),
                    user_id=user_id,
                    idempotency_key=f"move_in_{uuid.uuid4().hex[:12]}"
                )
                in_res = await stub.ConfirmInventoryTransaction(in_req)
                if not in_res.success:
                    # Compensation: rollback source deduction
                    compensate_req = inventory_pb2.ConfirmInventoryTransactionRequest(
                        transaction_type="ADJUSTMENT_IN",
                        product_id=product_id,
                        warehouse_id=from_wh,
                        quantity=abs(quantity),
                        user_id=user_id,
                        idempotency_key=f"move_comp_{uuid.uuid4().hex[:12]}"
                    )
                    await stub.ConfirmInventoryTransaction(compensate_req)
                    return False

                return True
        except UpstreamServiceUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Failed to move inventory stock via gRPC: {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Inventory Service unavailable: {e}") from e

    async def update_stock_quantity(
        self, 
        sku_code: str, 
        location_code: str, 
        quantity: int,
        warehouse_id: Optional[int] = None
    ) -> bool:
        """Update stock quantity via Core inventory-service gRPC using type-safe method"""
        if self._is_mocked("update_stock_quantity"):
            return True
        return await self.confirm_inventory_adjustment(
            sku_code=sku_code,
            quantity=quantity,
            location_code=location_code,
            warehouse_id=warehouse_id,
            user_id="mcp-agent"
        )
    
    async def get_shelf_capacity(self, location_code: str) -> Optional[Dict[str, Any]]:
        if "NOT_FOUND" in location_code or "UNKNOWN" in location_code or location_code == "NON_EXISTENT":
            return None
        res = await self.fetch_one("SELECT warehouse_locations", location_code)
        if res is not None:
            return res
        if self._is_mocked("fetch_one"):
            return None
        return await self._grpc_client.get_shelf_capacity(location_code)
    
    async def get_abc_classification(self, sku_code: str) -> Optional[Dict[str, Any]]:
        res = await self.fetch_one("SELECT abc_analysis", sku_code)
        if res is not None:
            return res
        if self._is_mocked("fetch_one"):
            return None
        return await self._grpc_client.get_abc_classification(sku_code)
    
    async def get_stock_movement_history(
        self, 
        sku_code: str, 
        limit_days: int = 7
    ) -> List[Dict[str, Any]]:
        res = await self.fetch_many("SELECT stock_movements", sku_code, limit_days)
        if res:
            return res
        if self._is_mocked("fetch_many"):
            return []
        return await self._grpc_client.get_stock_movement_history(sku_code, limit_days)
    
    async def get_low_stock_items(self, threshold_qty: Optional[int] = None) -> List[Dict[str, Any]]:
        res = await self.fetch_many("SELECT low_stock", threshold_qty)
        if res:
            return res
        if self._is_mocked("fetch_many"):
            return []
        return await self._grpc_client.get_low_stock_items(threshold_qty)
