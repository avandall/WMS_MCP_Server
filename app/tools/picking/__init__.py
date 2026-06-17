"""Smart picking tools"""

from app.tools.registry import ToolRegistry
from app.tools.picking.generate_picking_route import GeneratePickingRoute

def register_picking_tools(registry: ToolRegistry):
    """Register all picking tools"""
    registry.register(GeneratePickingRoute, category="picking")
