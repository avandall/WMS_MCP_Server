"""Inspect shelf capacity tool"""

from typing import Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_location_code
from app.utils.error_handlers import handle_tool_error


class InspectShelfCapacityInput(BaseModel):
    """Input schema for inspect_shelf_capacity"""
    location_code: str = Field(..., description="Location code (e.g., ZONE-A-ROW-02-SHELF-01)")


class InspectShelfCapacity(BaseTool):
    """Check shelf capacity and available space"""
    
    name = "inspect_shelf_capacity"
    description = "Check capacity and available space of a specific shelf/location based on physical volume"
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "location_code": {
                    "type": "string",
                    "description": "Location code (e.g., ZONE-A-ROW-02-SHELF-01)"
                }
            },
            "required": ["location_code"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = InspectShelfCapacityInput(**kwargs)
            
            # Validate input
            validate_location_code(input_data.location_code)
            
            # Connect to database
            await self.db.connect()
            
            # Get shelf capacity info
            shelf_info = await self.db.get_shelf_capacity(input_data.location_code)
            
            # Close connection
            await self.db.disconnect()
            
            if not shelf_info:
                return ToolResult(
                    success=False,
                    error=f"No shelf information found for location: {input_data.location_code}",
                    error_code="NOT_FOUND"
                )
            
            # Calculate available percentages
            if shelf_info.get('max_volume') and shelf_info.get('max_volume') > 0:
                shelf_info['volume_utilization_percent'] = round(
                    (shelf_info.get('current_volume', 0) / shelf_info['max_volume']) * 100, 2
                )
            
            if shelf_info.get('max_weight') and shelf_info.get('max_weight') > 0:
                shelf_info['weight_utilization_percent'] = round(
                    (shelf_info.get('current_weight', 0) / shelf_info['max_weight']) * 100, 2
                )
            
            return ToolResult(
                success=True,
                data=shelf_info
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
