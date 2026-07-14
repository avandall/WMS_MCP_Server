"""Get service logs devops tool"""

import subprocess
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.utils.error_handlers import handle_tool_error


class GetContainerLogsInput(BaseModel):
    """Input schema for get_container_logs"""
    service_name: str = Field(..., description="Service name (e.g., api-gateway, inventory-service, product-service, redis)")
    lines: Optional[int] = Field(50, description="Number of tail log lines to fetch")


class GetContainerLogs(BaseTool):
    """Retrieve logs from WMS system services (docker or local)"""
    
    name = "get_container_logs"
    description = "Retrieve the latest log lines of a specific running WMS microservice or container"
    
    def __init__(self, config):
        super().__init__(config)
        
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the service (e.g., api-gateway, inventory-service, product-service, redis)"
                },
                "lines": {
                    "type": "integer",
                    "description": "Number of tail lines to retrieve (default 50)"
                }
            },
            "required": ["service_name"]
        }
        
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            input_data = GetContainerLogsInput(**kwargs)
            service = input_data.service_name.lower()
            lines = input_data.lines or 50
            
            # 1. Try to fetch docker logs first
            # Get docker container matching service name
            try:
                check_cmd = ["docker", "ps", "-a", "--filter", f"name={service}", "--format", "{{.Names}}"]
                output = subprocess.check_output(check_cmd, text=True).strip()
                
                if output:
                    # Container found, retrieve logs
                    log_cmd = ["docker", "logs", "--tail", str(lines), output.split('\n')[0]]
                    logs = subprocess.check_output(log_cmd, stderr=subprocess.STDOUT, text=True)
                    return ToolResult(
                        success=True,
                        data={
                            "service": service,
                            "type": "docker_container",
                            "container_name": output.split('\n')[0],
                            "logs": logs
                        }
                    )
            except Exception as e:
                # Docker might not be running or command failed, fallback to process check
                pass
                
            # 2. Local process fallback check
            try:
                ps_cmd = f"ps aux | grep -i '{service}' | grep -v 'grep' | grep -v 'mcp'"
                ps_output = subprocess.check_output(ps_cmd, shell=True, text=True).strip()
                
                if ps_output:
                    return ToolResult(
                        success=True,
                        data={
                            "service": service,
                            "type": "local_process",
                            "status": "Running",
                            "process_info": ps_output,
                            "logs": "Service is running as a local process. Standard output logs are written to its respective active terminal session."
                        }
                    )
            except subprocess.CalledProcessError:
                # grep exited with 1 (no match)
                pass
                
            return ToolResult(
                success=False,
                error=f"No active container or local process found for service '{service}'",
                error_code="SERVICE_NOT_FOUND"
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
