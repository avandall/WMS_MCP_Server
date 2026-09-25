"""Adjust inventory for reason tool"""

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
    location_code: str = Field(..., description="Location code (e.g. AISLE-12-BAY-03)")
    reason: str = Field(..., description="Reason for adjustment (DAMAGED, LOST, FOUND, etc.)")
    quantity: int = Field(..., description="Quantity adjustment (can be positive or negative)")
    warehouse_id: int = Field(1, description="Warehouse ID")


class AdjustInventoryForReason(BaseTool):
    """Adjust inventory for specific reasons via Draft Proposal"""
    
    name = "adjust_inventory_for_reason"
    description = "Create a draft proposal to adjust inventory for reasons like damage, loss, or discovery (requires manager approval)"
    
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
                "reason": {
                    "type": "string",
                    "description": "Reason for adjustment (DAMAGED, LOST, FOUND, COUNT_DIFF, etc.)"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity adjustment (positive for increase, negative for decrease)"
                },
                "warehouse_id": {
                    "type": "integer",
                    "description": "Warehouse ID",
                    "default": 1
                }
            },
            "required": ["sku_code", "location_code", "reason", "quantity"]
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
            
            # Resolve IDs and explicit warehouse_id
            product_id = await self._resolve_product_id(input_data.sku_code)
            warehouse_id = input_data.warehouse_id
            
            # Call WMS Core inventory-service CreateDraftProposal gRPC (Maker-Checker compliance)
            async with grpc_client.inventory_stub() as stub:
                request = inventory_pb2.CreateDraftProposalRequest(
                    proposal_type="REASON_ADJUSTMENT",
                    sku_code=input_data.sku_code,
                    warehouse_id=warehouse_id,
                    location_code=input_data.location_code,
                    adjustment=input_data.quantity,
                    reason=input_data.reason,
                    requested_by="mcp-agent"
                )
                response = await stub.CreateDraftProposal(request)
                success = response.success
            
            # Release lock
            await self.redis.release_lock(lock_key, lock_value)
            
            # Close connection
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
                    "reason": input_data.reason,
                    "quantity": input_data.quantity,
                    "adjustment": input_data.quantity,
                    "status": status,
                    "message": f"Draft proposal {proposal_id} created successfully with status {status} for reason: {input_data.reason}. Awaiting manager approval."
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

