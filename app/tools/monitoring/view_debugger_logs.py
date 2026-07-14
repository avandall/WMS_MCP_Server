"""View debugger logs tool for AI self-healing diagnostics"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import os
import json

from app.tools.base import BaseTool, ToolResult
from app.utils.error_handlers import handle_tool_error


class ViewDebuggerLogsInput(BaseModel):
    """Input schema for view_debugger_logs"""
    limit: int = Field(default=50, ge=1, le=100, description="Limit of recent log lines to retrieve (max 100)")
    service: Optional[str] = Field(default=None, description="Optional service name filter (e.g. inventory-service)")
    trace_id: Optional[str] = Field(default=None, description="Optional OpenTelemetry Trace ID filter")


class ViewDebuggerLogs(BaseTool):
    """Read, search, and analyze recent WMS debug logs and traces"""
    
    name = "view_debugger_logs"
    description = "Read, search, and analyze recent WMS execution trace logs (gRPC calls, HTTP requests, Redis Streams events, LangGraph nodes) to diagnose system errors or get trace context for self-healing."
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get JSON input schema"""
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Limit of recent log lines to retrieve (max 100, defaults to 50)",
                    "minimum": 1,
                    "maximum": 100
                },
                "service": {
                    "type": "string",
                    "description": "Optional service name filter (e.g. inventory-service, api-gateway)"
                },
                "trace_id": {
                    "type": "string",
                    "description": "Optional OpenTelemetry Trace ID filter"
                }
            }
        }
        
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse inputs
            input_data = ViewDebuggerLogsInput(**kwargs)
            
            # Determine path to log file
            log_path = os.getenv("WMS_DEBUG_FILE_PATH", "/home/avandall1999/Projects/WMS_Root/wms_debug.log")
            
            if not os.path.exists(log_path):
                return ToolResult(
                    success=True,
                    data={
                        "log_file": log_path,
                        "exists": False,
                        "message": "No debugger logs found. Make sure WMS_DEBUG_ENABLED=true and WMS_DEBUG_WRITE_FILE=true are active.",
                        "logs": []
                    }
                )
                
            matched_logs: List[Dict[str, Any]] = []
            
            # Read log file lines
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            # Filter and extract matching logs starting from the end
            for line in reversed(lines):
                if len(matched_logs) >= input_data.limit:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    log_entry = json.loads(stripped)
                    
                    # Filter by service name if requested
                    if input_data.service and log_entry.get("service", "").lower() != input_data.service.lower():
                        continue
                        
                    # Filter by trace ID if requested
                    if input_data.trace_id and log_entry.get("trace_id") != input_data.trace_id:
                        continue
                        
                    matched_logs.append(log_entry)
                except Exception:
                    continue
                    
            # Restore chronological order (earliest logs first in the output subset)
            matched_logs.reverse()
            
            return ToolResult(
                success=True,
                data={
                    "log_file": log_path,
                    "exists": True,
                    "limit": input_data.limit,
                    "total_returned": len(matched_logs),
                    "logs": matched_logs
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
