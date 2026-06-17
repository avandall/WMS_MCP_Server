"""ABC analysis report tool"""

from typing import Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_sku_code
from app.utils.error_handlers import handle_tool_error


class ABCAnalysisReportInput(BaseModel):
    """Input schema for abc_analysis_report"""
    sku_code: str = Field(..., description="SKU code")


class ABCAnalysisReport(BaseTool):
    """Get ABC classification for a SKU"""
    
    name = "abc_analysis_report"
    description = "Get ABC classification based on outbound frequency and value (A: high, B: medium, C: low)"
    
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
                }
            },
            "required": ["sku_code"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = ABCAnalysisReportInput(**kwargs)
            
            # Validate input
            validate_sku_code(input_data.sku_code)
            
            # Connect to database
            await self.db.connect()
            
            # Get ABC classification
            abc_info = await self.db.get_abc_classification(input_data.sku_code)
            
            # Close connection
            await self.db.disconnect()
            
            if not abc_info:
                return ToolResult(
                    success=False,
                    error=f"No ABC classification found for SKU: {input_data.sku_code}",
                    error_code="NOT_FOUND"
                )
            
            # Add interpretation
            class_descriptions = {
                "A": "High value/high turnover items - should be placed near shipping area",
                "B": "Medium value/turnover items - should be placed in middle zones",
                "C": "Low value/turnover items - can be placed in remote areas"
            }
            
            abc_info['class_description'] = class_descriptions.get(
                abc_info.get('abc_class', 'C'),
                "Unknown classification"
            )
            
            return ToolResult(
                success=True,
                data=abc_info
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
