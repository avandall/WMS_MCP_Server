"""Error handling utilities for WMS tools"""

import logging
from typing import Optional, Dict, Any
from app.tools.base import ToolError, ToolResult

logger = logging.getLogger(__name__)


def handle_tool_error(error: Exception, tool_name: str = "unknown") -> ToolResult:
    """
    Handle tool errors and return standardized ToolResult
    
    Args:
        error: Exception that occurred
        tool_name: Name of the tool that failed
        
    Returns:
        ToolResult with error information
    """
    if isinstance(error, ToolError):
        # Already a ToolError, use its information
        return ToolResult(
            success=False,
            error=error.message,
            error_code=error.error_code,
            details=error.details
        )
    else:
        # Generic exception
        logger.error(f"Unexpected error in tool {tool_name}: {error}", exc_info=True)
        return ToolResult(
            success=False,
            error=str(error),
            error_code="UNEXPECTED_ERROR",
            details={"tool_name": tool_name}
        )


def log_error(
    error: Exception, 
    context: Optional[Dict[str, Any]] = None,
    level: str = "ERROR"
) -> None:
    """
    Log error with context information
    
    Args:
        error: Exception to log
        context: Additional context information
        level: Log level (ERROR, WARNING, INFO)
    """
    log_func = getattr(logger, level.lower(), logger.error)
    
    log_message = f"Error occurred: {type(error).__name__}: {str(error)}"
    
    if context:
        log_message += f" | Context: {context}"
    
    log_func(log_message, exc_info=True)


def create_error_response(
    message: str,
    error_code: str = "ERROR",
    details: Optional[Dict[str, Any]] = None
) -> ToolResult:
    """
    Create a standardized error response
    
    Args:
        message: Error message
        error_code: Error code
        details: Additional error details
        
    Returns:
        ToolResult with error information
    """
    return ToolResult(
        success=False,
        error=message,
        error_code=error_code,
        details=details
    )


def create_success_response(
    data: Optional[Dict[str, Any]] = None
) -> ToolResult:
    """
    Create a standardized success response
    
    Args:
        data: Response data
        
    Returns:
        ToolResult with success information
    """
    return ToolResult(
        success=True,
        data=data
    )
