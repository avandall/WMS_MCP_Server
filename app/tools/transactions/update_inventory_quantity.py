"""Update inventory quantity tool"""

from typing import Dict, Any, Literal
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.clients.redis_client import RedisClient
from app.utils.validators import (
    validate_sku_code, 
    validate_location_code, 
    validate_quantity,
    validate_action
)
from app.utils.error_handlers import handle_tool_error
import uuid


class UpdateInventoryQuantityInput(BaseModel):
    """Input schema for update_inventory_quantity"""
    sku_code: str = Field(..., description="SKU code")
    location_code: str = Field(..., description="Location code")
    action: Literal["INCREASE", "DECREASE"] = Field(..., description="Action: INCREASE or DECREASE")
    quantity: int = Field(..., description="Quantity to increase/decrease")


class UpdateInventoryQuantity(BaseTool):
    """Update inventory quantity at a specific location"""
    
    name = "update_inventory_quantity"
    description = "Increase or decrease inventory quantity at a specific location (used for inbound/outbound operations)"
    
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
            
            # Connect to services
            await self.db.connect()
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
            
            # Calculate quantity change
            quantity_change = input_data.quantity if input_data.action == "INCREASE" else -input_data.quantity
            
            # Update inventory
            success = await self.db.update_stock_quantity(
                sku_code=input_data.sku_code,
                location_code=input_data.location_code,
                quantity=quantity_change
            )
            
            # Release lock
            await self.redis.release_lock(lock_key, lock_value)
            
            # Close connections
            await self.db.disconnect()
            await self.redis.disconnect()
            
            if not success:
                return ToolResult(
                    success=False,
                    error="Failed to update inventory quantity",
                    error_code="UPDATE_FAILED"
                )
            
            # Invalidate cache
            await self.redis.cache_delete(f"stock:{input_data.sku_code}")
            
            return ToolResult(
                success=True,
                data={
                    "sku_code": input_data.sku_code,
                    "location_code": input_data.location_code,
                    "action": input_data.action,
                    "quantity": input_data.quantity,
                    "message": f"Successfully {input_data.action.lower()}d inventory by {input_data.quantity}"
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
