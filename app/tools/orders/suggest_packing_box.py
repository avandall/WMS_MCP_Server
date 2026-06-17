"""Suggest packing box tool"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_order_id
from app.utils.error_handlers import handle_tool_error


class SuggestPackingBoxInput(BaseModel):
    """Input schema for suggest_packing_box"""
    order_id: str = Field(..., description="Order ID")


class SuggestPackingBox(BaseTool):
    """Suggest optimal packing box based on order items"""
    
    name = "suggest_packing_box"
    description = "Calculate total volume/weight of order items and suggest optimal box size to minimize shipping costs"
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Order ID"
                }
            },
            "required": ["order_id"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = SuggestPackingBoxInput(**kwargs)
            
            # Validate input
            validate_order_id(input_data.order_id)
            
            # Connect to database
            await self.db.connect()
            
            # Get order items with product dimensions
            query = """
                SELECT 
                    oi.sku_code,
                    oi.quantity,
                    p.length,
                    p.width,
                    p.height,
                    p.weight,
                    (p.length * p.width * p.height) as item_volume,
                    (p.weight * oi.quantity) as total_weight
                FROM order_items oi
                JOIN products p ON oi.sku_code = p.sku_code
                WHERE oi.order_id = $1
            """
            
            order_items = await self.db.fetch_many(query, input_data.order_id)
            
            # Close connection
            await self.db.disconnect()
            
            if not order_items:
                return ToolResult(
                    success=False,
                    error=f"No items found for order: {input_data.order_id}",
                    error_code="NOT_FOUND"
                )
            
            # Calculate total dimensions
            total_volume = sum(item.get('item_volume', 0) * item.get('quantity', 1) for item in order_items)
            total_weight = sum(item.get('total_weight', 0) for item in order_items)
            
            # Get available box sizes
            available_boxes = await self._get_available_boxes()
            
            # Find optimal box
            recommendations = self._find_optimal_boxes(
                total_volume, 
                total_weight, 
                available_boxes
            )
            
            return ToolResult(
                success=True,
                data={
                    "order_id": input_data.order_id,
                    "order_items": order_items,
                    "total_volume_cm3": round(total_volume, 2),
                    "total_weight_kg": round(total_weight, 2),
                    "item_count": len(order_items),
                    "recommendations": recommendations,
                    "selected_recommendation": recommendations[0] if recommendations else None
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
    
    async def _get_available_boxes(self) -> List[Dict[str, Any]]:
        """Get available packing box sizes"""
        query = """
            SELECT 
                box_id,
                name,
                length,
                width,
                height,
                max_weight,
                (length * width * height) as volume
            FROM packing_boxes
            WHERE active = true
            ORDER BY volume ASC
        """
        return await self.db.fetch_many(query)
    
    def _find_optimal_boxes(
        self, 
        total_volume: float, 
        total_weight: float,
        available_boxes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find optimal boxes based on volume and weight"""
        recommendations = []
        
        for box in available_boxes:
            box_volume = box.get('volume', 0)
            max_weight = box.get('max_weight', 0)
            
            # Check if box can accommodate the order
            if box_volume >= total_volume and max_weight >= total_weight:
                # Calculate efficiency (how much wasted space)
                wasted_space = box_volume - total_volume
                efficiency = (total_volume / box_volume) * 100 if box_volume > 0 else 0
                
                recommendations.append({
                    "box_id": box.get('box_id'),
                    "name": box.get('name'),
                    "dimensions": {
                        "length": box.get('length'),
                        "width": box.get('width'),
                        "height": box.get('height')
                    },
                    "volume_cm3": box_volume,
                    "max_weight_kg": max_weight,
                    "efficiency_percent": round(efficiency, 2),
                    "wasted_space_cm3": round(wasted_space, 2),
                    "recommendation_score": self._calculate_recommendation_score(efficiency, wasted_space)
                })
        
        # Sort by recommendation score (higher is better)
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def _calculate_recommendation_score(self, efficiency: float, wasted_space: float) -> float:
        """Calculate recommendation score"""
        # Higher efficiency and lower wasted space = higher score
        score = efficiency - (wasted_space / 10000)  # Penalize wasted space
        return round(score, 2)
