"""Monitoring and concurrency tools"""

from app.tools.registry import ToolRegistry
from app.tools.monitoring.check_redis_locks import CheckRedisLocks
from app.tools.monitoring.get_stock_movement_history import GetStockMovementHistory
from app.tools.monitoring.view_message_queue_status import ViewMessageQueueStatus

def register_monitoring_tools(registry: ToolRegistry):
    """Register all monitoring tools"""
    registry.register(CheckRedisLocks, category="monitoring")
    registry.register(GetStockMovementHistory, category="monitoring")
    registry.register(ViewMessageQueueStatus, category="monitoring")
