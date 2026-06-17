"""Alert and reporting tools"""

from app.tools.registry import ToolRegistry
from app.tools.alerts.get_low_stock_report import GetLowStockReport
from app.tools.alerts.create_system_alert import CreateSystemAlert

def register_alerts_tools(registry: ToolRegistry):
    """Register all alert tools"""
    registry.register(GetLowStockReport, category="alerts")
    registry.register(CreateSystemAlert, category="alerts")
