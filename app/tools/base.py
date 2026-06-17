"""Base tool class and common functionality for all WMS tools"""

from typing import Any, Dict, Optional, Type
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ToolError(Exception):
    """Custom exception for tool errors"""
    
    def __init__(self, message: str, error_code: str = "TOOL_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ToolResult(BaseModel):
    """Standard result structure for all tools"""
    
    success: bool = Field(..., description="Whether the tool execution was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Tool output data")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    error_code: Optional[str] = Field(None, description="Error code for categorization")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Execution timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BaseTool(ABC):
    """Base class for all WMS MCP tools"""
    
    name: str = ""
    description: str = ""
    
    def __init__(self, config: Any = None):
        """Initialize tool with configuration"""
        self.config = config
        self.logger = logger
        
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult: Standardized tool result
        """
        pass
    
    def get_input_schema(self) -> Dict[str, Any]:
        """
        Get the input schema for this tool
        
        Returns:
            Dict containing the input schema definition
        """
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """
        Get the output schema for this tool
        
        Returns:
            Dict containing the output schema definition
        """
        return ToolResult.schema()
    
    def validate_input(self, input_data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Validate input data against schema
        
        Args:
            input_data: Input data to validate
            schema: Schema to validate against
            
        Returns:
            bool: True if valid, raises ToolError if invalid
        """
        try:
            # Basic validation - can be enhanced with pydantic
            required = schema.get("required", [])
            for field in required:
                if field not in input_data:
                    raise ToolError(
                        f"Missing required field: {field}",
                        error_code="VALIDATION_ERROR",
                        details={"missing_field": field}
                    )
            return True
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(
                f"Input validation failed: {str(e)}",
                error_code="VALIDATION_ERROR"
            )
    
    async def execute_with_timing(self, **kwargs) -> ToolResult:
        """
        Execute tool with timing measurement
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with execution time
        """
        import time
        start_time = time.time()
        
        try:
            result = await self.execute(**kwargs)
            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = round(execution_time, 2)
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'EXECUTION_ERROR') if isinstance(e, ToolError) else 'EXECUTION_ERROR'
            
            return ToolResult(
                success=False,
                error=error_msg,
                error_code=error_code,
                execution_time_ms=round(execution_time, 2)
            )
    
    def log_execution(self, kwargs: Dict[str, Any], result: ToolResult):
        """Log tool execution for debugging and monitoring"""
        log_data = {
            "tool": self.name,
            "success": result.success,
            "execution_time_ms": result.execution_time_ms,
            "timestamp": result.timestamp
        }
        
        if not result.success:
            log_data["error"] = result.error
            log_data["error_code"] = result.error_code
            self.logger.error(f"Tool execution failed: {log_data}")
        else:
            self.logger.info(f"Tool execution successful: {log_data}")
