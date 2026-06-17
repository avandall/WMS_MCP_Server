"""Transaction and movement tools"""

from app.tools.registry import ToolRegistry
from app.tools.transactions.update_inventory_quantity import UpdateInventoryQuantity
from app.tools.transactions.move_stock_between_locations import MoveStockBetweenLocations
from app.tools.transactions.adjust_inventory_for_reason import AdjustInventoryForReason

def register_transaction_tools(registry: ToolRegistry):
    """Register all transaction tools"""
    registry.register(UpdateInventoryQuantity, category="transactions")
    registry.register(MoveStockBetweenLocations, category="transactions")
    registry.register(AdjustInventoryForReason, category="transactions")
