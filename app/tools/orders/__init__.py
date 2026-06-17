"""Order management tools"""

from app.tools.registry import ToolRegistry
from app.tools.orders.get_order_status_details import GetOrderStatusDetails
from app.tools.orders.suggest_packing_box import SuggestPackingBox

def register_order_tools(registry: ToolRegistry):
    """Register all order tools"""
    registry.register(GetOrderStatusDetails, category="orders")
    registry.register(SuggestPackingBox, category="orders")
