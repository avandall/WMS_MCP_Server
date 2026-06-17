"""Get stock movement history tool"""

from typing import Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_sku_code, validate_quantity
from app.utils.error_handlers import handle_tool_error


class GetStockMovementHistoryInput(BaseModel):
    """Input schema for get_stock_movement_history"""
    sku_code: str = Field(..., description="SKU code")
    limit_days: int = Field(7, description="Number of days to look back (default: 7)")


class GetStockMovementHistory(BaseTool):
    """Get stock movement history for audit trail"""
    
    name = "get_stock_movement_history"
    description = "Get complete audit trail of stock movements for a SKU within a time range"
    
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
                    "description": "SKU code"
                },
                "limit_days": {
                    "type": "integer",
                    "description": "Number of days to look back (default: 7)",
                    "default": 7
                }
            },
            "required": ["sku_code"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = GetStockMovementHistoryInput(**kwargs)
            
            # Validate inputs
            validate_sku_code(input_data.sku_code)
            validate_quantity(input_data.limit_days, allow_zero=True)
            
            # Connect to database
            await self.db.connect()
            
            # Get movement history
            movements = await self.db.get_stock_movement_history(
                sku_code=input_data.sku_code,
                limit_days=input_data.limit_days
            )
            
            # Close connection
            await self.db.disconnect()
            
            if not movements:
                return ToolResult(
                    success=True,
                    data={
                        "sku_code": input_data.sku_code,
                        "limit_days": input_data.limit_days,
                        "movements": [],
                        "total_movements": 0,
                        "message": "No movement history found for this SKU in the specified time range"
                    }
                )
            
            # Analyze movements
            analysis = self._analyze_movements(movements)
            
            return ToolResult(
                success=True,
                data={
                    "sku_code": input_data.sku_code,
                    "limit_days": input_data.limit_days,
                    "movements": movements,
                    "total_movements": len(movements),
                    "analysis": analysis
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
    
    def _analyze_movements(self, movements: list) -> Dict[str, Any]:
        """Analyze movement patterns"""
        analysis = {
            "movement_types": {},
            "total_quantity_moved": 0,
            "net_change": 0,
            "most_active_location": None,
            "movement_frequency": {}
        }
        
        location_counts = {}
        
        for movement in movements:
            # Count movement types
            movement_type = movement.get('movement_type', 'UNKNOWN')
            analysis["movement_types"][movement_type] = analysis["movement_types"].get(movement_type, 0) + 1
            
            # Calculate totals
            quantity = movement.get('quantity', 0)
            analysis["total_quantity_moved"] += abs(quantity)
            
            # Calculate net change
            if movement_type == 'INBOUND':
                analysis["net_change"] += quantity
            elif movement_type == 'OUTBOUND':
                analysis["net_change"] -= quantity
            elif movement_type == 'ADJUSTMENT':
                analysis["net_change"] += quantity
            
            # Track location activity
            from_loc = movement.get('from_location')
            to_loc = movement.get('to_location')
            
            if from_loc:
                location_counts[from_loc] = location_counts.get(from_loc, 0) + 1
            if to_loc:
                location_counts[to_loc] = location_counts.get(to_loc, 0) + 1
        
        # Find most active location
        if location_counts:
            analysis["most_active_location"] = max(location_counts, key=location_counts.get)
        
        return analysis
