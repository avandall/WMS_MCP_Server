"""Update inventory quantity tool"""

import re
import uuid
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.redis_client import RedisClient
from app.integration.grpc_client import grpc_client
from app.utils.validators import (
    validate_sku_code, 
    validate_location_code, 
    validate_quantity,
    validate_action
)
from app.utils.error_handlers import handle_tool_error

from app.gen.wms.inventory.v1 import inventory_pb2
from app.gen.wms.product.v1 import product_pb2


class UpdateInventoryQuantityInput(BaseModel):
    """Input schema for update_inventory_quantity"""
    sku_code: str = Field(..., description="SKU code or Product ID")
    location_code: str = Field(..., description="Location code or Warehouse ID")
    action: Literal["INCREASE", "DECREASE"] = Field(..., description="Action: INCREASE or DECREASE")
    quantity: int = Field(..., description="Quantity to increase/decrease")


class UpdateInventoryQuantity(BaseTool):
    """Update inventory quantity at a specific location"""
    
    name = "update_inventory_quantity"
    description = "Increase or decrease inventory quantity at a specific warehouse/location via core services"
    
    def __init__(self, config):
        super().__init__(config)
        self.redis = RedisClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "sku_code": {
                    "type": "string",
                    "description": "SKU code or Product ID"
                },
                "location_code": {
                    "type": "string",
                    "description": "Location code or Warehouse ID (e.g., WH-1 or 1)"
                },
                "action": {
                    "type": "string",
                    "enum": ["INCREASE", "DECREASE"],
                    "description": "Action: INCREASE or DECREASE"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity to increase/decrease (must be positive)"
                }
            },
            "required": ["sku_code", "location_code", "action", "quantity"]
        }
        
    async def _resolve_product_id(self, sku_code: str) -> int:
        """Resolve SKU code or ID to product_id via grpc_core_client with cache"""
        from app.clients.grpc_core_client import grpc_core_client
        return await grpc_core_client.resolve_product_id(sku_code)

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        lock_key = None
        try:
            # Parse input
            input_data = UpdateInventoryQuantityInput(**kwargs)
            
            # Validate inputs
            validate_sku_code(input_data.sku_code)
            validate_location_code(input_data.location_code)
            validate_action(input_data.action, ["INCREASE", "DECREASE"])
            validate_quantity(input_data.quantity, allow_zero=False)
            
            # Connect to Redis
            await self.redis.connect()
            
            # Acquire distributed lock to prevent race conditions
            lock_key = f"lock:inventory:{input_data.sku_code}:{input_data.location_code}"
            lock_value = str(uuid.uuid4())
            
            lock_acquired = await self.redis.acquire_lock(lock_key, lock_value, expire=30)
            if not lock_acquired:
                return ToolResult(
                    success=False,
                    error="Could not acquire lock - another operation is in progress",
                    error_code="LOCK_ACQUISITION_FAILED"
                )
            
            # Resolve product_id and warehouse_id
            product_id = await self._resolve_product_id(input_data.sku_code)
            
            # Extract warehouse_id from location_code string
            warehouse_id = 1
            digits = re.findall(r'\d+', input_data.location_code)
            if digits:
                warehouse_id = int(digits[0])
                
            # Determine transaction type
            tx_type = "ADJUSTMENT_IN" if input_data.action == "INCREASE" else "ADJUSTMENT_OUT"
            
            # Call WMS Core inventory-service via gRPC ConfirmInventoryTransaction
            async with grpc_client.inventory_stub() as stub:
                request = inventory_pb2.ConfirmInventoryTransactionRequest(
                    transaction_type=tx_type,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=input_data.quantity,
                    user_id="mcp-agent",
                    idempotency_key=f"confirm_{uuid.uuid4().hex[:12]}"
                )
                response = await stub.ConfirmInventoryTransaction(request)
                success = response.success
            
            # Release lock
            await self.redis.release_lock(lock_key, lock_value)
            
            # Close connections
            await self.redis.disconnect()
            
            if not success:
                return ToolResult(
                    success=False,
                    error="Failed to update inventory quantity via WMS Core service",
                    error_code="UPDATE_FAILED"
                )
            
            # Invalidate cache
            await self.redis.cache_delete(f"stock:{input_data.sku_code}")
            
            return ToolResult(
                success=True,
                data={
                    "sku_code": input_data.sku_code,
                    "product_id": product_id,
                    "warehouse_id": warehouse_id,
                    "location_code": input_data.location_code,
                    "action": input_data.action,
                    "quantity": input_data.quantity,
                    "transaction_id": response.transaction_id,
                    "message": f"Successfully {input_data.action.lower()}d inventory by {input_data.quantity} via Core gRPC service"
                }
            )
            
        except Exception as e:
            # Ensure lock is released on error with exact token (TECH-BUG-02)
            if lock_key and hasattr(self, 'redis') and 'lock_value' in locals() and lock_value:
                try:
                    await self.redis.release_lock(lock_key, lock_value)
                except Exception:
                    pass
            return handle_tool_error(e, self.name)

