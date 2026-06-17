"""Tool registry system for managing and discovering MCP tools"""

from typing import Dict, Type, List, Optional, Any
from app.tools.base import BaseTool, ToolResult
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all WMS MCP tools"""
    
    def __init__(self):
        """Initialize empty tool registry"""
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._tool_instances: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}
        
    def register(self, tool_class: Type[BaseTool], category: str = "general") -> None:
        """
        Register a tool class
        
        Args:
            tool_class: Tool class to register
            category: Category for grouping tools (e.g., 'inventory', 'transactions')
            
        Raises:
            ValueError: If tool name already exists
        """
        tool_name = tool_class.name
        
        if not tool_name:
            raise ValueError("Tool class must have a 'name' attribute")
            
        if tool_name in self._tools:
            logger.warning(f"Tool '{tool_name}' already registered, skipping duplicate")
            return
            
        self._tools[tool_name] = tool_class
        
        # Add to category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool_name)
        
        logger.info(f"Registered tool: {tool_name} in category: {category}")
    
    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool by name
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            
            # Remove from categories
            for category, tools in self._categories.items():
                if tool_name in tools:
                    tools.remove(tool_name)
                    
            # Remove instance if exists
            if tool_name in self._tool_instances:
                del self._tool_instances[tool_name]
                
            logger.info(f"Unregistered tool: {tool_name}")
    
    def get_tool(self, tool_name: str, config: Any = None) -> Optional[BaseTool]:
        """
        Get a tool instance by name
        
        Args:
            tool_name: Name of tool to get
            config: Configuration to pass to tool
            
        Returns:
            Tool instance or None if not found
        """
        if tool_name not in self._tools:
            logger.warning(f"Tool '{tool_name}' not found in registry")
            return None
            
        # Return existing instance if available and config matches
        if tool_name in self._tool_instances:
            return self._tool_instances[tool_name]
            
        # Create new instance
        tool_class = self._tools[tool_name]
        instance = tool_class(config)
        self._tool_instances[tool_name] = instance
        
        return instance
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all registered tools with their metadata
        
        Returns:
            List of tool information dictionaries
        """
        tools_info = []
        
        for tool_name, tool_class in self._tools.items():
            # Create temporary instance to get schemas
            temp_instance = tool_class(None)
            
            tools_info.append({
                "name": tool_name,
                "description": temp_instance.description,
                "input_schema": temp_instance.get_input_schema(),
                "output_schema": temp_instance.get_output_schema()
            })
            
        return tools_info
    
    def list_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        List tools in a specific category
        
        Args:
            category: Category name
            
        Returns:
            List of tool information dictionaries
        """
        if category not in self._categories:
            return []
            
        tools_info = []
        for tool_name in self._categories[category]:
            tool_class = self._tools.get(tool_name)
            if tool_class:
                temp_instance = tool_class(None)
                tools_info.append({
                    "name": tool_name,
                    "description": temp_instance.description,
                    "input_schema": temp_instance.get_input_schema(),
                    "output_schema": temp_instance.get_output_schema()
                })
                
        return tools_info
    
    def get_categories(self) -> List[str]:
        """
        Get list of all categories
        
        Returns:
            List of category names
        """
        return list(self._categories.keys())
    
    def tool_exists(self, tool_name: str) -> bool:
        """
        Check if a tool is registered
        
        Args:
            tool_name: Name of tool to check
            
        Returns:
            bool: True if tool exists
        """
        return tool_name in self._tools
    
    def get_tool_count(self) -> int:
        """
        Get total number of registered tools
        
        Returns:
            int: Number of tools
        """
        return len(self._tools)
    
    def clear(self) -> None:
        """Clear all registered tools"""
        self._tools.clear()
        self._tool_instances.clear()
        self._categories.clear()
        logger.info("Cleared all tools from registry")


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_global_registry() -> ToolRegistry:
    """
    Get or create the global tool registry
    
    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
