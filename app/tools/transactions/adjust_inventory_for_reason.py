"""Adjust inventory for reason tool"""

from typing import Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.clients.redis_client import RedisClient
from app.utils.validators import (
    validate_sku_code,
    validate_location_code,
    validate_quantity
)
from app.utils.error_handlers import handle_tool_error
import uuid
from datetime import datetime


class AdjustInventoryForReasonInput(BaseModel):
    """Input schema for adjust_inventory_for_reason"""
    sku_code: str = Field(..., description="SKU code")
    location_code: str = Field(..., description="Location code")
    reason: str = Field(..., description="Reason for adjustment (DAMAGED, LOST, FOUND, etc.)")
    quantity: int = Field(..., description="Quantity adjustment (can be positive or negative)")


class AdjustInventoryForReason(BaseTool):
    """Adjust inventory for specific reasons (stock adjustment)"""
    
    name = "adjust_inventory_for_reason"
    description = "Adjust inventory quantity for reasons like damage, loss, or discovery after inventory count"
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
        self.redis = RedisClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "sku_code": {
                    "type": "string",
                    "description": "SKU code"
                },
                "location_code": {
                    "type": "string",
                    "description": "Location code"
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
            
            # Connect to services
            await self.db.connect()
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
            
            # Perform adjustment in transaction with audit record
            queries = [
                {
                    "query": """
                        UPDATE inventory_stock
                        SET 
                            physical_qty = physical_qty + $1,
                            available_qty = available_qty + $1,
                            last_updated = NOW()
                        WHERE sku_code = $2 AND location_code = $3
                    """,
                    "params": [input_data.quantity, input_data.sku_code, input_data.location_code]
                },
                {
                    "query": """
                        INSERT INTO stock_movements (
                            sku_code, from_location, to_location, quantity, 
                            movement_type, reason, reference_id, created_at, created_by
                        ) VALUES ($1, $2, $3, $4, 'ADJUSTMENT', $5, $6, NOW(), 'SYSTEM')
                    """,
                    "params": [
                        input_data.sku_code,
                        input_data.location_code,
                        input_data.location_code,
                        input_data.quantity,
                        input_data.reason,
                        f"ADJ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                    ]
                }
            ]
            
            success = await self.db.execute_transaction(queries)
            
            # Release lock
            await self.redis.release_lock(lock_key, lock_value)
            
            # Close connections
            await self.db.disconnect()
            await self.redis.disconnect()
            
            if not success:
                return ToolResult(
                    success=False,
                    error="Failed to complete inventory adjustment",
                    error_code="ADJUSTMENT_FAILED"
                )
            
            # Invalidate cache
            await self.redis.cache_delete(f"stock:{input_data.sku_code}")
            
            return ToolResult(
                success=True,
                data={
                    "sku_code": input_data.sku_code,
                    "location_code": input_data.location_code,
                    "reason": input_data.reason,
                    "quantity": input_data.quantity,
                    "message": f"Successfully adjusted inventory by {input_data.quantity} for reason: {input_data.reason}"
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
