"""Inventory management tools"""

from app.tools.registry import ToolRegistry
from app.tools.inventory.check_stock_availability import CheckStockAvailability
from app.tools.inventory.inspect_shelf_capacity import InspectShelfCapacity
from app.tools.inventory.abc_analysis_report import ABCAnalysisReport
from app.tools.inventory.smart_slotting_optimizer import SmartSlottingOptimizer

def register_inventory_tools(registry: ToolRegistry):
    """Register all inventory tools"""
    registry.register(CheckStockAvailability, category="inventory")
    registry.register(InspectShelfCapacity, category="inventory")
    registry.register(ABCAnalysisReport, category="inventory")
    registry.register(SmartSlottingOptimizer, category="inventory")
