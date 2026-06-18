"""Performance profiling script for WMS MCP Server"""

import cProfile
import pstats
import io
import asyncio
from app.tools.inventory.check_stock_availability import CheckStockAvailabilityTool
from app.clients.database_client import DatabaseClient
from app.config import Config


async def profile_tool_execution():
    """Profile tool execution performance"""
    
    # Setup
    config = Config()
    db_client = DatabaseClient(config)
    tool = CheckStockAvailabilityTool(db_client)
    
    # Create profiler
    profiler = cProfile.Profile()
    
    # Profile tool execution
    profiler.enable()
    
    # Execute tool multiple times
    for _ in range(100):
        try:
            await tool.execute({
                "sku_code": "SKU-1060-6GB",
                "warehouse_id": 1
            })
        except Exception:
            pass
    
    profiler.disable()
    
    # Print statistics
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)
    print(s.getvalue())


if __name__ == "__main__":
    asyncio.run(profile_tool_execution())
