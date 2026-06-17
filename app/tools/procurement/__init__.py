"""Procurement tools"""

from app.tools.registry import ToolRegistry
from app.tools.procurement.verify_incoming_po import VerifyIncomingPO

def register_procurement_tools(registry: ToolRegistry):
    """Register all procurement tools"""
    registry.register(VerifyIncomingPO, category="procurement")
