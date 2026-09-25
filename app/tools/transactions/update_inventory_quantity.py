"""Update inventory quantity tool"""

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
    location_code: str = Field(..., description="Location code (e.g. AISLE-12-BAY-03)")
    action: Literal["INCREASE", "DECREASE"] = Field(..., description="Action: INCREASE or DECREASE")
    quantity: int = Field(..., description="Quantity to increase/decrease")
    warehouse_id: int = Field(1, description="Warehouse ID")


class UpdateInventoryQuantity(BaseTool):
    """Update inventory quantity at a specific location via Draft Proposal"""
    
    name = "update_inventory_quantity"
    description = "Create a draft proposal to increase or decrease inventory quantity at a warehouse location (requires manager approval)"
    
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
                    "description": "Location code (e.g. AISLE-12-BAY-03)"
                },
                "action": {
                    "type": "string",
                    "enum": ["INCREASE", "DECREASE"],
                    "description": "Action: INCREASE or DECREASE"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity to increase/decrease (must be positive)"
                },
                "warehouse_id": {
                    "type": "integer",
                    "description": "Warehouse ID",
                    "default": 1
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
            
            # Resolve product_id and explicit warehouse_id
            product_id = await self._resolve_product_id(input_data.sku_code)
            warehouse_id = input_data.warehouse_id
                
            # Calculate adjustment (+qty for INCREASE, -qty for DECREASE)
            adjustment = input_data.quantity if input_data.action == "INCREASE" else -input_data.quantity
            
            # Call WMS Core inventory-service via gRPC CreateDraftProposal (Maker-Checker compliance)
            async with grpc_client.inventory_stub() as stub:
                request = inventory_pb2.CreateDraftProposalRequest(
                    proposal_type="QUANTITY_UPDATE",
                    sku_code=input_data.sku_code,
                    warehouse_id=warehouse_id,
                    location_code=input_data.location_code,
                    adjustment=adjustment,
                    reason=f"AI Agent quantity update: {input_data.action} {input_data.quantity}",
                    requested_by="mcp-agent"
                )
                response = await stub.CreateDraftProposal(request)
                success = response.success
            
            # Release lock
            await self.redis.release_lock(lock_key, lock_value)
            
            # Close connections
            await self.redis.disconnect()
            
            if not success:
                return ToolResult(
                    success=False,
                    error=response.message or "Failed to create draft proposal via WMS Core service",
                    error_code="PROPOSAL_CREATION_FAILED"
                )
            
            # Invalidate cache
            await self.redis.cache_delete(f"stock:{input_data.sku_code}")
            
            proposal = response.proposal
            proposal_id = getattr(proposal, "proposal_id", "") if proposal else ""
            status = getattr(proposal, "status", "DRAFT_PROPOSAL") if proposal else "DRAFT_PROPOSAL"
            
            return ToolResult(
                success=True,
                data={
                    "proposal_id": proposal_id,
                    "sku_code": input_data.sku_code,
                    "product_id": product_id,
                    "warehouse_id": warehouse_id,
                    "location_code": input_data.location_code,
                    "action": input_data.action,
                    "quantity": input_data.quantity,
                    "adjustment": adjustment,
                    "status": status,
                    "message": f"Draft proposal {proposal_id} created successfully with status {status}. Awaiting manager approval."
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

