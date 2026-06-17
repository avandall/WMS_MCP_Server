"""Move stock between locations tool"""

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


class MoveStockBetweenLocationsInput(BaseModel):
    """Input schema for move_stock_between_locations"""
    sku_code: str = Field(..., description="SKU code")
    from_location: str = Field(..., description="Source location code")
    to_location: str = Field(..., description="Destination location code")
    quantity: int = Field(..., description="Quantity to move")


class MoveStockBetweenLocations(BaseTool):
    """Move stock between locations (internal transfer)"""
    
    name = "move_stock_between_locations"
    description = "Move a specific quantity of stock from one location to another (internal transfer)"
    
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
                "from_location": {
                    "type": "string",
                    "description": "Source location code"
                },
                "to_location": {
                    "type": "string",
                    "description": "Destination location code"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity to move"
                }
            },
            "required": ["sku_code", "from_location", "to_location", "quantity"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        lock_key = None
        try:
            # Parse input
            input_data = MoveStockBetweenLocationsInput(**kwargs)
            
            # Validate inputs
            validate_sku_code(input_data.sku_code)
            validate_location_code(input_data.from_location)
            validate_location_code(input_data.to_location)
            validate_quantity(input_data.quantity, allow_zero=False)
            
            if input_data.from_location == input_data.to_location:
                return ToolResult(
                    success=False,
                    error="Source and destination locations cannot be the same",
                    error_code="INVALID_OPERATION"
                )
            
            # Connect to services
            await self.db.connect()
            await self.redis.connect()
            
            # Acquire distributed locks for both locations
            lock_key_from = f"lock:inventory:{input_data.sku_code}:{input_data.from_location}"
            lock_key_to = f"lock:inventory:{input_data.sku_code}:{input_data.to_location}"
            lock_value = str(uuid.uuid4())
            
            lock_from = await self.redis.acquire_lock(lock_key_from, lock_value, expire=30)
            lock_to = await self.redis.acquire_lock(lock_key_to, lock_value, expire=30)
            
            if not lock_from or not lock_to:
                # Release any acquired locks
                if lock_from:
                    await self.redis.release_lock(lock_key_from, lock_value)
                if lock_to:
                    await self.redis.release_lock(lock_key_to, lock_value)
                
                return ToolResult(
                    success=False,
                    error="Could not acquire locks - another operation is in progress",
                    error_code="LOCK_ACQUISITION_FAILED"
                )
            
            # Check if source has enough stock
            source_stock = await self.db.get_stock_info(
                sku_code=input_data.sku_code,
                warehouse_id=None  # Get all warehouses
            )
            
            # Find specific location stock
            source_location_stock = None
            if source_stock:
                if isinstance(source_stock, list):
                    source_location_stock = next(
                        (s for s in source_stock if s.get('location_code') == input_data.from_location),
                        None
                    )
                elif source_stock.get('location_code') == input_data.from_location:
                    source_location_stock = source_stock
            
            if not source_location_stock or source_location_stock.get('available_qty', 0) < input_data.quantity:
                # Release locks
                await self.redis.release_lock(lock_key_from, lock_value)
                await self.redis.release_lock(lock_key_to, lock_value)
                
                return ToolResult(
                    success=False,
                    error=f"Insufficient stock at source location. Available: {source_location_stock.get('available_qty', 0) if source_location_stock else 0}",
                    error_code="INSUFFICIENT_STOCK"
                )
            
            # Perform transfer in transaction
            queries = [
                {
                    "query": """
                        UPDATE inventory_stock
                        SET 
                            physical_qty = physical_qty - $1,
                            available_qty = available_qty - $1,
                            last_updated = NOW()
                        WHERE sku_code = $2 AND location_code = $3
                    """,
                    "params": [input_data.quantity, input_data.sku_code, input_data.from_location]
                },
                {
                    "query": """
                        UPDATE inventory_stock
                        SET 
                            physical_qty = physical_qty + $1,
                            available_qty = available_qty + $1,
                            last_updated = NOW()
                        WHERE sku_code = $2 AND location_code = $3
                    """,
                    "params": [input_data.quantity, input_data.sku_code, input_data.to_location]
                }
            ]
            
            success = await self.db.execute_transaction(queries)
            
            # Release locks
            await self.redis.release_lock(lock_key_from, lock_value)
            await self.redis.release_lock(lock_key_to, lock_value)
            
            # Close connections
            await self.db.disconnect()
            await self.redis.disconnect()
            
            if not success:
                return ToolResult(
                    success=False,
                    error="Failed to complete stock transfer",
                    error_code="TRANSFER_FAILED"
                )
            
            # Invalidate cache
            await self.redis.cache_delete(f"stock:{input_data.sku_code}")
            
            return ToolResult(
                success=True,
                data={
                    "sku_code": input_data.sku_code,
                    "from_location": input_data.from_location,
                    "to_location": input_data.to_location,
                    "quantity": input_data.quantity,
                    "message": f"Successfully moved {input_data.quantity} units from {input_data.from_location} to {input_data.to_location}"
                }
            )
            
        except Exception as e:
            # Ensure locks are released on error
            if lock_key and hasattr(self, 'redis'):
                try:
                    await self.redis.release_lock(lock_key, str(uuid.uuid4()))
                except:
                    pass
            return handle_tool_error(e, self.name)
