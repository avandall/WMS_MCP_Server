"""Create system alert tool"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_action
from app.utils.error_handlers import handle_tool_error
from datetime import datetime
import uuid


class CreateSystemAlertInput(BaseModel):
    """Input schema for create_system_alert"""
    alert_type: str = Field(..., description="Alert type: CRITICAL, WARNING, or INFO")
    message: str = Field(..., description="Detailed alert message")
    source: Optional[str] = Field(None, description="Alert source (e.g., tool name)")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional alert details")


class CreateSystemAlert(BaseTool):
    """Create system alert for monitoring"""
    
    name = "create_system_alert"
    description = "Create system alert for critical issues detected by AI (e.g., warehouse capacity, system locks)"
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "alert_type": {
                    "type": "string",
                    "enum": ["CRITICAL", "WARNING", "INFO"],
                    "description": "Alert type: CRITICAL, WARNING, or INFO"
                },
                "message": {
                    "type": "string",
                    "description": "Detailed alert message"
                },
                "source": {
                    "type": "string",
                    "description": "Alert source (e.g., tool name)"
                },
                "details": {
                    "type": "object",
                    "description": "Additional alert details"
                }
            },
            "required": ["alert_type", "message"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = CreateSystemAlertInput(**kwargs)
            
            # Validate alert type
            validate_action(input_data.alert_type, ["CRITICAL", "WARNING", "INFO"])
            
            # Generate alert ID
            alert_id = f"ALT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
            
            # Connect to database
            await self.db.connect()
            
            # Insert alert into database
            query = """
                INSERT INTO system_alerts (
                    alert_id, alert_type, message, source, details, 
                    resolved, created_at
                ) VALUES ($1, $2, $3, $4, $5, false, NOW())
            """
            
            await self.db.execute(
                query,
                alert_id,
                input_data.alert_type,
                input_data.message,
                input_data.source or "MCP_SERVER",
                input_data.details or {}
            )
            
            # Close connection
            await self.db.disconnect()
            
            # Determine if immediate notification is needed
            needs_notification = input_data.alert_type == "CRITICAL"
            
            return ToolResult(
                success=True,
                data={
                    "alert_id": alert_id,
                    "alert_type": input_data.alert_type,
                    "message": input_data.message,
                    "source": input_data.source or "MCP_SERVER",
                    "created_at": datetime.utcnow().isoformat(),
                    "needs_notification": needs_notification,
                    "notification_action": "Immediate escalation required" if needs_notification else "Logged for monitoring"
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
