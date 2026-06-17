"""MCP Server implementation for WMS tools"""

import logging
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import json

from app.config import get_config
from app.tools.registry import get_global_registry
from app.tools.base import ToolResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize configuration and registry
config = get_config()
registry = get_global_registry()


class WMSServer:
    """WMS MCP Server implementation"""
    
    def __init__(self):
        """Initialize the WMS MCP server"""
        self.server = Server("wms-mcp-server")
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Set up MCP server handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available tools"""
            tools_info = registry.list_tools()
            
            mcp_tools = []
            for tool_info in tools_info:
                tool_name = tool_info["name"]
                
                # Check if tool is enabled
                if not config.is_tool_enabled(tool_name):
                    logger.debug(f"Tool {tool_name} is disabled, skipping")
                    continue
                
                mcp_tools.append(Tool(
                    name=tool_name,
                    description=tool_info["description"],
                    inputSchema=tool_info["input_schema"]
                ))
            
            logger.info(f"Listed {len(mcp_tools)} enabled tools")
            return mcp_tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Call a specific tool"""
            logger.info(f"Tool called: {name} with arguments: {arguments}")
            
            # Check if tool is enabled
            if not config.is_tool_enabled(name):
                error_msg = f"Tool '{name}' is disabled"
                logger.warning(error_msg)
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": error_msg,
                        "error_code": "TOOL_DISABLED"
                    })
                )]
            
            # Get tool instance
            tool = registry.get_tool(name, config)
            if not tool:
                error_msg = f"Tool '{name}' not found"
                logger.error(error_msg)
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": error_msg,
                        "error_code": "TOOL_NOT_FOUND"
                    })
                )]
            
            # Execute tool
            try:
                result = await tool.execute_with_timing(**arguments)
                
                # Log execution
                tool.log_execution(arguments, result)
                
                # Return result as JSON
                return [TextContent(
                    type="text",
                    text=json.dumps(result.dict())
                )]
                
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}", exc_info=True)
                error_result = ToolResult(
                    success=False,
                    error=str(e),
                    error_code="EXECUTION_ERROR"
                )
                return [TextContent(
                    type="text",
                    text=json.dumps(error_result.dict())
                )]
    
    async def run(self):
        """Run the MCP server"""
        logger.info(f"Starting WMS MCP Server v{config.APP_VERSION}")
        logger.info(f"Debug mode: {config.DEBUG}")
        logger.info(f"Registered tools: {registry.get_tool_count()}")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def register_tools_from_categories():
    """Register tools from all categories"""
    # This will be populated when we implement actual tools
    # For now, we'll register placeholder tools from each category
    
    from app.tools.inventory import register_inventory_tools
    from app.tools.transactions import register_transaction_tools
    from app.tools.monitoring import register_monitoring_tools
    from app.tools.alerts import register_alerts_tools
    
    # Register tools from each category
    register_inventory_tools(registry)
    register_transaction_tools(registry)
    register_monitoring_tools(registry)
    register_alerts_tools(registry)
    
    logger.info(f"Registered {registry.get_tool_count()} tools from all categories")


async def main():
    """Main entry point"""
    # Register all tools
    await register_tools_from_categories()
    
    # Create and run server
    server = WMSServer()
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
