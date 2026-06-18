"""Database query optimization script for WMS MCP Server"""

import asyncio
import time
from app.clients.database_client import DatabaseClient
from app.config import Config


async def analyze_query_performance():
    """Analyze and optimize database query performance"""
    
    # Setup
    config = Config()
    db_client = DatabaseClient(config)
    await db_client.connect()
    
    # Test queries
    queries = [
        "SELECT * FROM inventory WHERE sku_code = $1",
        "SELECT * FROM orders WHERE status = $1",
        "SELECT * FROM locations WHERE zone_id = $1",
    ]
    
    for query in queries:
        # Measure query execution time
        start_time = time.time()
        
        try:
            await db_client.fetch_many(query, "TEST")
            execution_time = time.time() - start_time
            
            print(f"Query: {query}")
            print(f"Execution time: {execution_time:.4f}s")
            
            if execution_time > 0.1:
                print("WARNING: Slow query detected")
                print("Consider adding index or optimizing query")
            
        except Exception as e:
            print(f"Error executing query: {e}")
    
    await db_client.disconnect()


if __name__ == "__main__":
    asyncio.run(analyze_query_performance())
