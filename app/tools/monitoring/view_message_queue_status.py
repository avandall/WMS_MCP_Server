"""View message queue status tool"""

from typing import Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.queue_client import QueueClient
from app.utils.error_handlers import handle_tool_error


class ViewMessageQueueStatusInput(BaseModel):
    """Input schema for view_message_queue_status"""
    queue_name: str = Field(..., description="Queue name (e.g., wms.order.process)")


class ViewMessageQueueStatus(BaseTool):
    """Check message queue backlog status"""
    
    name = "view_message_queue_status"
    description = "Get number of messages waiting in message queue to identify processing bottlenecks"
    
    def __init__(self, config):
        super().__init__(config)
        self.queue = QueueClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "queue_name": {
                    "type": "string",
                    "description": "Queue name (e.g., wms.order.process)"
                }
            },
            "required": ["queue_name"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = ViewMessageQueueStatusInput(**kwargs)
            
            # Connect to queue
            await self.queue.connect()
            
            # Get queue status
            queue_status = await self.queue.get_queue_status(input_data.queue_name)
            
            # Also get order queue backlog for context
            order_backlog = await self.queue.get_order_queue_backlog()
            
            # Close connection
            await self.queue.disconnect()
            
            # Analyze status
            analysis = self._analyze_queue_status(queue_status, order_backlog)
            
            return ToolResult(
                success=True,
                data={
                    "queue_name": input_data.queue_name,
                    "queue_status": queue_status,
                    "order_backlog": order_backlog,
                    "analysis": analysis
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
    
    def _analyze_queue_status(self, queue_status: Dict[str, Any], order_backlog: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze queue status and provide insights"""
        analysis = {
            "health_status": "healthy",
            "message_count": 0,
            "consumer_count": 0,
            "backlog_severity": "low",
            "recommendation": "No action needed"
        }
        
        if "error" not in queue_status:
            analysis["message_count"] = queue_status.get("message_count", 0)
            analysis["consumer_count"] = queue_status.get("consumer_count", 0)
            
            # Determine health status
            message_count = analysis["message_count"]
            consumer_count = analysis["consumer_count"]
            
            if message_count == 0:
                analysis["health_status"] = "idle"
                analysis["recommendation"] = "Queue is empty - normal if no orders are being processed"
            elif consumer_count == 0 and message_count > 0:
                analysis["health_status"] = "critical"
                analysis["backlog_severity"] = "high"
                analysis["recommendation"] = "No consumers detected - workers may be down"
            elif message_count > 1000:
                analysis["health_status"] = "warning"
                analysis["backlog_severity"] = "medium"
                analysis["recommendation"] = f"High backlog ({message_count} messages) - consider scaling consumers"
            elif message_count > 100:
                analysis["health_status"] = "warning"
                analysis["backlog_severity"] = "low"
                analysis["recommendation"] = f"Moderate backlog ({message_count} messages) - monitor closely"
            else:
                analysis["health_status"] = "healthy"
                analysis["recommendation"] = f"Normal operations ({message_count} messages, {consumer_count} consumers)"
        
        # Check overall order processing health
        total_backlog = sum(
            status.get("message_count", 0) 
            for status in order_backlog.values() 
            if isinstance(status, dict) and "error" not in status
        )
        
        if total_backlog > 5000:
            analysis["system_wide_alert"] = f"High system-wide backlog: {total_backlog} messages across all order queues"
        
        return analysis
