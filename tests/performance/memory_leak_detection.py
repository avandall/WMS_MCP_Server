"""Memory leak detection script for WMS MCP Server"""

import gc
import tracemalloc
import asyncio
from app.tools.inventory.check_stock_availability import CheckStockAvailabilityTool
from app.clients.database_client import DatabaseClient
from app.config import Config


async def detect_memory_leaks():
    """Detect memory leaks during tool execution"""
    
    # Start tracing memory allocations
    tracemalloc.start()
    
    # Setup
    config = Config()
    db_client = DatabaseClient(config)
    tool = CheckStockAvailabilityTool(db_client)
    
    # Get initial snapshot
    snapshot1 = tracemalloc.take_snapshot()
    
    # Execute tool multiple times
    for i in range(1000):
        try:
            await tool.execute({
                "sku_code": "SKU-1060-6GB",
                "warehouse_id": 1
            })
        except Exception:
            pass
        
        # Force garbage collection every 100 iterations
        if i % 100 == 0:
            gc.collect()
    
    # Get final snapshot
    snapshot2 = tracemalloc.take_snapshot()
    
    # Compare snapshots
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    print("Top memory allocations:")
    for stat in top_stats[:10]:
        print(stat)
    
    # Stop tracing
    tracemalloc.stop()


if __name__ == "__main__":
    asyncio.run(detect_memory_leaks())
