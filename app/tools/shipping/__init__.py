"""Shipping tools"""

from app.tools.registry import ToolRegistry
from app.tools.shipping.create_shipping_label import CreateShippingLabel

def register_shipping_tools(registry: ToolRegistry):
    """Register all shipping tools"""
    registry.register(CreateShippingLabel, category="shipping")
