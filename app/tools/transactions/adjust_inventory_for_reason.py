"""Adjust inventory for reason tool"""

import re
import uuid
from typing import Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.redis_client import RedisClient
from app.integration.grpc_client import grpc_client
from app.utils.validators import (
    validate_sku_code,
    validate_location_code,
    validate_quantity
)
from app.utils.error_handlers import handle_tool_error

from app.gen.wms.inventory.v1 import inventory_pb2
from app.gen.wms.product.v1 import product_pb2


class AdjustInventoryForReasonInput(BaseModel):
    """Input schema for adjust_inventory_for_reason"""
    sku_code: str = Field(..., description="SKU code or Product ID")
    location_code: str = Field(..., description="Location code or Warehouse ID")
    reason: str = Field(..., description="Reason for adjustment (DAMAGED, LOST, FOUND, etc.)")
    quantity: int = Field(..., description="Quantity adjustment (can be positive or negative)")


class AdjustInventoryForReason(BaseTool):
    """Adjust inventory for specific reasons (stock adjustment)"""
    
    name = "adjust_inventory_for_reason"
    description = "Adjust inventory quantity for reasons like damage, loss, or discovery via core services"
    
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
                    "description": "Location code or Warehouse ID"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for adjustment (DAMAGED, LOST, FOUND, COUNT_DIFF, etc.)"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity adjustment (positive for increase, negative for decrease)"
                }
            },
            "required": ["sku_code", "location_code", "reason", "quantity"]
        }
        
    async def _resolve_product_id(self, sku_code: str) -> int:
        """Resolve SKU code or ID to product_id"""
        try:
            cleaned = sku_code.upper().replace("SKU-", "")
            return int(cleaned)
        except ValueError:
            async with grpc_client.product_stub() as stub:
                response = await stub.ListProducts(product_pb2.ListProductsRequest())
                for product in response.products:
                    if product.name.upper() == sku_code.upper():
                        return product.product_id
            raise ValueError(f"Product/SKU '{sku_code}' could not be resolved to a product ID")
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        lock_key = None
        try:
            # Parse input
            input_data = AdjustInventoryForReasonInput(**kwargs)
            
            # Validate inputs
            validate_sku_code(input_data.sku_code)
            validate_location_code(input_data.location_code)
            validate_quantity(abs(input_data.quantity), allow_zero=False)
            
            valid_reasons = ["DAMAGED", "LOST", "FOUND", "COUNT_DIFF", "EXPIRED", "QUALITY_HOLD", "OTHER"]
            if input_data.reason.upper() not in valid_reasons:
                return ToolResult(
                    success=False,
                    error=f"Invalid reason. Valid reasons: {', '.join(valid_reasons)}",
                    error_code="INVALID_REASON"
                )
            
            # Connect to Redis
            await self.redis.connect()
            
            # Acquire distributed lock
            lock_key = f"lock:inventory:{input_data.sku_code}:{input_data.location_code}"
            lock_value = str(uuid.uuid4())
            
            lock_acquired = await self.redis.acquire_lock(lock_key, lock_value, expire=30)
            if not lock_acquired:
                return ToolResult(
                    success=False,
                    error="Could not acquire lock - another operation is in progress",
                    error_code="LOCK_ACQUISITION_FAILED"
                )
            
            # Resolve IDs
            product_id = await self._resolve_product_id(input_data.sku_code)
            
            warehouse_id = 1
            digits = re.findall(r'\d+', input_data.location_code)
            if digits:
                warehouse_id = int(digits[0])
                
            # Determine direct transaction type based on sign of quantity
            tx_type = "ADJUSTMENT_IN" if input_data.quantity > 0 else "ADJUSTMENT_OUT"
            abs_qty = abs(input_data.quantity)
            
            # Call WMS Core inventory-service ConfirmInventoryTransaction gRPC
            async with grpc_client.inventory_stub() as stub:
                request = inventory_pb2.ConfirmInventoryTransactionRequest(
                    transaction_type=tx_type,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=abs_qty,
                    user_id="mcp-agent",
                    idempotency_key=f"confirm_adj_{uuid.uuid4().hex[:12]}"
                )
                response = await stub.ConfirmInventoryTransaction(request)
                success = response.success
            
            # Release lock
            await self.redis.release_lock(lock_key, lock_value)
            
            # Close connection
            await self.redis.disconnect()
            
            if not success:
                return ToolResult(
                    success=False,
                    error="Failed to complete inventory adjustment via WMS Core service",
                    error_code="ADJUSTMENT_FAILED"
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
                    "reason": input_data.reason,
                    "quantity": input_data.quantity,
                    "transaction_id": response.transaction_id,
                    "message": f"Successfully adjusted inventory by {input_data.quantity} for reason: {input_data.reason} via Core gRPC service"
                }
            )
            
        except Exception as e:
            # Ensure lock is released on error
            if lock_key and hasattr(self, 'redis'):
                try:
                    await self.redis.release_lock(lock_key, str(uuid.uuid4()))
                except:
                    pass
            return handle_tool_error(e, self.name)

