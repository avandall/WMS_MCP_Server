"""Get low stock report tool"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_quantity
from app.utils.error_handlers import handle_tool_error


class GetLowStockReportInput(BaseModel):
    """Input schema for get_low_stock_report"""
    threshold_qty: Optional[int] = Field(None, description="Custom threshold quantity (optional)")


class GetLowStockReport(BaseTool):
    """Get report of items with low stock"""
    
    name = "get_low_stock_report"
    description = "Scan database for items with available quantity at or below safety stock level"
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "threshold_qty": {
                    "type": "integer",
                    "description": "Custom threshold quantity (optional, uses safety_stock if not provided)"
                }
            },
            "required": []
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = GetLowStockReportInput(**kwargs)
            
            # Validate threshold if provided
            if input_data.threshold_qty is not None:
                validate_quantity(input_data.threshold_qty, allow_zero=True)
            
            # Connect to database
            await self.db.connect()
            
            # Get low stock items
            low_stock_items = await self.db.get_low_stock_items(input_data.threshold_qty)
            
            # Close connection
            await self.db.disconnect()
            
            if not low_stock_items:
                return ToolResult(
                    success=True,
                    data={
                        "low_stock_items": [],
                        "total_items": 0,
                        "message": "No items found with low stock"
                    }
                )
            
            # Analyze low stock
            analysis = self._analyze_low_stock(low_stock_items)
            
            return ToolResult(
                success=True,
                data={
                    "low_stock_items": low_stock_items,
                    "total_items": len(low_stock_items),
                    "threshold_used": input_data.threshold_qty or "safety_stock",
                    "analysis": analysis
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
    
    def _analyze_low_stock(self, items: list) -> Dict[str, Any]:
        """Analyze low stock patterns"""
        analysis = {
            "critical_items": [],  # Items with zero stock
            "warning_items": [],   # Items below safety stock but above zero
            "total_below_safety": len(items),
            "warehouses_affected": set(),
            "avg_below_safety_by": 0
        }
        
        total_below = 0
        
        for item in items:
            available_qty = item.get('available_qty', 0)
            safety_stock = item.get('safety_stock', 0)
            warehouse_id = item.get('warehouse_id')
            
            if warehouse_id:
                analysis["warehouses_affected"].add(warehouse_id)
            
            below_by = safety_stock - available_qty if safety_stock > available_qty else 0
            total_below += below_by
            
            if available_qty == 0:
                analysis["critical_items"].append({
                    "sku_code": item.get('sku_code'),
                    "warehouse_id": warehouse_id,
                    "safety_stock": safety_stock
                })
            else:
                analysis["warning_items"].append({
                    "sku_code": item.get('sku_code'),
                    "warehouse_id": warehouse_id,
                    "available_qty": available_qty,
                    "safety_stock": safety_stock,
                    "below_by": below_by
                })
        
        if items:
            analysis["avg_below_safety_by"] = round(total_below / len(items), 2)
        
        analysis["warehouses_affected"] = list(analysis["warehouses_affected"])
        analysis["critical_count"] = len(analysis["critical_items"])
        analysis["warning_count"] = len(analysis["warning_items"])
        
        # Generate recommendations
        if analysis["critical_count"] > 0:
            analysis["recommendation"] = f"URGENT: {analysis['critical_count']} items are completely out of stock. Immediate replenishment required."
        elif analysis["warning_count"] > 10:
            analysis["recommendation"] = f"WARNING: {analysis['warning_count']} items are below safety stock. Consider expedited orders."
        else:
            analysis["recommendation"] = f"{analysis['warning_count']} items below safety stock. Monitor and plan replenishment."
        
        return analysis
