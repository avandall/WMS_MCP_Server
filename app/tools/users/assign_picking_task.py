"""Assign picking task tool"""

from typing import Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_user_id
from app.utils.error_handlers import handle_tool_error
from datetime import datetime
import uuid


class AssignPickingTaskInput(BaseModel):
    """Input schema for assign_picking_task"""
    task_id: str = Field(..., description="Task ID")
    user_id: str = Field(..., description="User ID to assign task to")


class AssignPickingTask(BaseTool):
    """Assign picking task to available worker"""
    
    name = "assign_picking_task"
    description = "Assign picking or inventory task to a specific worker for execution"
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID"
                },
                "user_id": {
                    "type": "string",
                    "description": "User ID to assign task to"
                }
            },
            "required": ["task_id", "user_id"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = AssignPickingTaskInput(**kwargs)
            
            # Validate input
            validate_user_id(input_data.user_id)
            
            # Connect to database
            await self.db.connect()
            
            # Check if user exists and is available
            user_query = """
                SELECT user_id, username, status, current_task_id
                FROM users
                WHERE user_id = $1
            """
            
            user_info = await self.db.fetch_one(user_query, input_data.user_id)
            
            if not user_info:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"User not found: {input_data.user_id}",
                    error_code="NOT_FOUND"
                )
            
            if user_info.get('status') != 'AVAILABLE':
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"User is not available. Current status: {user_info.get('status')}",
                    error_code="USER_UNAVAILABLE"
                )
            
            # Check if task exists and is unassigned
            task_query = """
                SELECT task_id, task_type, status, order_id, priority
                FROM picking_tasks
                WHERE task_id = $1
            """
            
            task_info = await self.db.fetch_one(task_query, input_data.task_id)
            
            if not task_info:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"Task not found: {input_data.task_id}",
                    error_code="NOT_FOUND"
                )
            
            if task_info.get('status') != 'UNASSIGNED':
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"Task is not available for assignment. Current status: {task_info.get('status')}",
                    error_code="TASK_UNAVAILABLE"
                )
            
            # Assign task to user in transaction
            queries = [
                {
                    "query": """
                        UPDATE picking_tasks
                        SET 
                            assigned_user_id = $1,
                            status = 'ASSIGNED',
                            assigned_at = NOW()
                        WHERE task_id = $2
                    """,
                    "params": [input_data.user_id, input_data.task_id]
                },
                {
                    "query": """
                        UPDATE users
                        SET 
                            status = 'BUSY',
                            current_task_id = $1
                        WHERE user_id = $2
                    """,
                    "params": [input_data.task_id, input_data.user_id]
                }
            ]
            
            success = await self.db.execute_transaction(queries)
            
            # Close connection
            await self.db.disconnect()
            
            if not success:
                return ToolResult(
                    success=False,
                    error="Failed to assign task",
                    error_code="ASSIGNMENT_FAILED"
                )
            
            return ToolResult(
                success=True,
                data={
                    "task_id": input_data.task_id,
                    "user_id": input_data.user_id,
                    "username": user_info.get('username'),
                    "task_type": task_info.get('task_type'),
                    "order_id": task_info.get('order_id'),
                    "priority": task_info.get('priority'),
                    "assigned_at": datetime.utcnow().isoformat(),
                    "message": f"Task {input_data.task_id} successfully assigned to {user_info.get('username')}"
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
