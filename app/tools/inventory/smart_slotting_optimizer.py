"""Smart slotting optimizer tool"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_sku_code, validate_quantity
from app.utils.error_handlers import handle_tool_error


class SmartSlottingOptimizerInput(BaseModel):
    """Input schema for smart_slotting_optimizer"""
    sku_code: str = Field(..., description="SKU code")
    quantity: int = Field(..., description="Quantity of items to be stored")


class SmartSlottingOptimizer(BaseTool):
    """Suggest optimal storage location based on ABC classification"""
    
    name = "smart_slotting_optimizer"
    description = "Suggest optimal storage location for items based on ABC classification (e.g., Class A items near shipping area)"
    
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
                "quantity": {
                    "type": "integer",
                    "description": "Quantity of items to be stored"
                }
            },
            "required": ["sku_code", "quantity"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = SmartSlottingOptimizerInput(**kwargs)
            
            # Validate inputs
            validate_sku_code(input_data.sku_code)
            validate_quantity(input_data.quantity)
            
            # Connect to database
            await self.db.connect()
            
            # Get ABC classification
            abc_info = await self.db.get_abc_classification(input_data.sku_code)
            
            if not abc_info:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"No ABC classification found for SKU: {input_data.sku_code}",
                    error_code="NOT_FOUND"
                )
            
            abc_class = abc_info.get('abc_class', 'C')
            
            # Get available locations based on ABC class
            # This is a simplified logic - in production, this would use more sophisticated algorithms
            suggested_locations = await self._get_suggested_locations(
                abc_class, 
                input_data.quantity
            )
            
            # Close connection
            await self.db.disconnect()
            
            # Prioritization logic
            recommendations = []
            for location in suggested_locations:
                recommendations.append({
                    "location_code": location['location_code'],
                    "zone": location.get('zone_id'),
                    "priority_score": self._calculate_priority_score(abc_class, location),
                    "available_volume": location.get('available_volume', 0),
                    "available_weight": location.get('available_weight', 0),
                    "reason": self._get_recommendation_reason(abc_class, location)
                })
            
            # Sort by priority score
            recommendations.sort(key=lambda x: x['priority_score'], reverse=True)
            
            return ToolResult(
                success=True,
                data={
                    "sku_code": input_data.sku_code,
                    "quantity": input_data.quantity,
                    "abc_class": abc_class,
                    "recommendations": recommendations[:5],  # Top 5 recommendations
                    "total_recommendations": len(recommendations)
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
    
    async def _get_suggested_locations(self, abc_class: str, quantity: int) -> List[Dict[str, Any]]:
        """Get suggested locations based on ABC class and quantity"""
        # Simplified query - in production this would be more sophisticated
        zone_priority = {
            "A": ["ZONE-A", "ZONE-B"],  # Near shipping
            "B": ["ZONE-B", "ZONE-C"],  # Middle zones
            "C": ["ZONE-C", "ZONE-D"]   # Remote areas
        }
        
        preferred_zones = zone_priority.get(abc_class, ["ZONE-C"])
        
        # Query for available locations in preferred zones
        query = """
            SELECT 
                location_code,
                zone_id,
                row_id,
                shelf_id,
                available_volume,
                available_weight
            FROM warehouse_locations
            WHERE zone_id = ANY($1)
            AND available_volume > 0
            ORDER BY 
                CASE zone_id
                    WHEN 'ZONE-A' THEN 1
                    WHEN 'ZONE-B' THEN 2
                    WHEN 'ZONE-C' THEN 3
                    ELSE 4
                END,
                available_volume DESC
            LIMIT 10
        """
        
        locations = await self.db.fetch_many(query, preferred_zones)
        return locations
    
    def _calculate_priority_score(self, abc_class: str, location: Dict[str, Any]) -> float:
        """Calculate priority score for a location"""
        score = 0.0
        
        # Zone score based on ABC class
        zone_scores = {
            "A": {"ZONE-A": 100, "ZONE-B": 80, "ZONE-C": 60, "ZONE-D": 40},
            "B": {"ZONE-A": 60, "ZONE-B": 100, "ZONE-C": 80, "ZONE-D": 60},
            "C": {"ZONE-A": 40, "ZONE-B": 60, "ZONE-C": 100, "ZONE-D": 80}
        }
        
        zone_id = location.get('zone_id', 'ZONE-D')
        score += zone_scores.get(abc_class, {}).get(zone_id, 50)
        
        # Volume bonus
        available_volume = location.get('available_volume', 0)
        score += min(available_volume / 1000, 20)  # Max 20 points for volume
        
        return round(score, 2)
    
    def _get_recommendation_reason(self, abc_class: str, location: Dict[str, Any]) -> str:
        """Get recommendation reason"""
        zone_id = location.get('zone_id', 'UNKNOWN')
        
        reasons = {
            "A": f"Class A item - recommended placement in {zone_id} for fast access to shipping area",
            "B": f"Class B item - suitable placement in {zone_id} for balanced access",
            "C": f"Class C item - acceptable placement in {zone_id} for cost-effective storage"
        }
        
        return reasons.get(abc_class, f"Suitable location in {zone_id}")
