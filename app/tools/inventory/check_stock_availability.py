"""Check stock availability tool"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_sku_code, validate_warehouse_id
from app.utils.error_handlers import handle_tool_error


class CheckStockAvailabilityInput(BaseModel):
    """Input schema for check_stock_availability"""
    sku_code: str = Field(..., description="SKU code (e.g., SKU-1060-6GB)")
    warehouse_id: Optional[int] = Field(None, description="Warehouse ID")


class CheckStockAvailability(BaseTool):
    """Check stock availability for a SKU"""
    
    name = "check_stock_availability"
    description = "Get physical and available stock quantities for a SKU at a specific warehouse"
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "sku_code": {
                    "type": "string",
                    "description": "SKU code (e.g., SKU-1060-6GB)"
                },
                "warehouse_id": {
                    "type": "integer",
                    "description": "Warehouse ID (optional)"
                }
            },
            "required": ["sku_code"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = CheckStockAvailabilityInput(**kwargs)
            
            # Validate inputs
            validate_sku_code(input_data.sku_code)
            validate_warehouse_id(input_data.warehouse_id)
            
            # Connect to database
            await self.db.connect()
            
            # Get stock info
            stock_info = await self.db.get_stock_info(
                sku_code=input_data.sku_code,
                warehouse_id=input_data.warehouse_id
            )
            
            # Close connection
            await self.db.disconnect()
            
            if not stock_info:
                return ToolResult(
                    success=False,
                    error=f"No stock information found for SKU: {input_data.sku_code}",
                    error_code="NOT_FOUND"
                )
            
            return ToolResult(
                success=True,
                data=stock_info
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
