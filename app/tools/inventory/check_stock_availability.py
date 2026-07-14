"""Check stock availability tool"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.integration.grpc_client import grpc_client
from app.utils.validators import validate_sku_code, validate_warehouse_id
from app.utils.error_handlers import handle_tool_error

from app.gen.wms.inventory.v1 import inventory_pb2
from app.gen.wms.product.v1 import product_pb2


class CheckStockAvailabilityInput(BaseModel):
    """Input schema for check_stock_availability"""
    sku_code: str = Field(..., description="SKU code or Product ID (e.g., SKU-1060-6GB or 1)")
    warehouse_id: Optional[int] = Field(None, description="Warehouse ID")


class CheckStockAvailability(BaseTool):
    """Check stock availability for a SKU"""
    
    name = "check_stock_availability"
    description = "Get physical and available stock quantities for a SKU/product at a specific warehouse"
    
    def __init__(self, config):
        super().__init__(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "sku_code": {
                    "type": "string",
                    "description": "SKU code or Product ID (e.g., SKU-1 or 1)"
                },
                "warehouse_id": {
                    "type": "integer",
                    "description": "Warehouse ID (optional)"
                }
            },
            "required": ["sku_code"]
        }
        
    async def _resolve_product_id(self, sku_code: str) -> int:
        """Resolve SKU code or ID to product_id"""
        try:
            # If numeric or SKU-number format
            cleaned = sku_code.upper().replace("SKU-", "")
            return int(cleaned)
        except ValueError:
            # Look up product by name from product-service
            async with grpc_client.product_stub() as stub:
                response = await stub.ListProducts(product_pb2.ListProductsRequest())
                for product in response.products:
                    if product.name.upper() == sku_code.upper():
                        return product.product_id
            raise ValueError(f"Product/SKU '{sku_code}' not found or could not be resolved to a product ID")
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = CheckStockAvailabilityInput(**kwargs)
            
            # Validate inputs
            validate_sku_code(input_data.sku_code)
            validate_warehouse_id(input_data.warehouse_id)
            
            # Resolve product ID
            try:
                product_id = await self._resolve_product_id(input_data.sku_code)
            except ValueError as e:
                return ToolResult(
                    success=False,
                    error=str(e),
                    error_code="NOT_FOUND"
                )
            
            # Default warehouse_id to 1 if not specified (local standard)
            wh_id = input_data.warehouse_id or 1
            
            # Query stock availability from inventory-service via gRPC
            async with grpc_client.inventory_stub() as stub:
                request = inventory_pb2.GetAvailabilityRequest(
                    product_id=product_id,
                    warehouse_id=wh_id
                )
                response = await stub.GetAvailability(request)
            
            stock_info = {
                "sku_code": input_data.sku_code,
                "product_id": response.product_id,
                "warehouse_id": response.warehouse_id,
                "physical_qty": response.physical_qty,
                "available_qty": response.available_qty,
                "reserved_qty": response.reserved_qty,
                "location_code": "dynamic"
            }
            
            return ToolResult(
                success=True,
                data=stock_info
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)

