"""Database optimization for WMS MCP Server"""

import asyncpg
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager


class DatabaseConnectionPool:
    """Optimized database connection pool"""
    
    def __init__(self, min_size: int = 5, max_size: int = 20):
        self.min_size = min_size
        self.max_size = max_size
        self.pool = None
    
    async def initialize(self, dsn: str):
        """Initialize connection pool"""
        self.pool = await asyncpg.create_pool(
            dsn,
            min_size=self.min_size,
            max_size=self.max_size,
            command_timeout=30
        )
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire connection from pool"""
        async with self.pool.acquire() as connection:
            yield connection
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get pool status"""
        if not self.pool:
            return {"status": "not_initialized"}
        
        return {
            "min_size": self.pool._minsize,
            "max_size": self.pool._maxsize,
            "current_size": self.pool._size,
            "available": self.pool._queue.qsize()
        }


class QueryOptimizer:
    """Query optimization utilities"""
    
    def __init__(self):
        self.query_cache = {}
        self.index_recommendations = {}
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query for optimization opportunities"""
        recommendations = []
        
        # Check for SELECT *
        if "SELECT *" in query.upper():
            recommendations.append("Avoid SELECT *, specify only needed columns")
        
        # Check for missing WHERE clause
        if "WHERE" not in query.upper():
            recommendations.append("Consider adding WHERE clause to limit results")
        
        # Check for ORDER BY without LIMIT
        if "ORDER BY" in query.upper() and "LIMIT" not in query.upper():
            recommendations.append("Consider adding LIMIT to ORDER BY queries")
        
        return {
            "query": query,
            "recommendations": recommendations,
            "estimated_cost": self._estimate_query_cost(query)
        }
    
    def _estimate_query_cost(self, query: str) -> int:
        """Estimate query cost (simplified)"""
        cost = 1
        
        if "JOIN" in query.upper():
            cost += 10
        
        if "ORDER BY" in query.upper():
            cost += 5
        
        if "GROUP BY" in query.upper():
            cost += 5
        
        if "HAVING" in query.upper():
            cost += 3
        
        return cost
    
    def recommend_indexes(self, table: str, query: str) -> List[str]:
        """Recommend indexes for query optimization"""
        recommendations = []
        
        # Extract WHERE clause columns
        if "WHERE" in query.upper():
            where_clause = query.upper().split("WHERE")[1].split(" ")[0]
            recommendations.append(f"CREATE INDEX idx_{table}_{where_clause} ON {table}({where_clause})")
        
        # Extract JOIN columns
        if "JOIN" in query.upper():
            join_parts = [part for part in query.upper().split("JOIN") if "ON" in part]
            for part in join_parts:
                on_clause = part.split("ON")[1].split("=")[0].strip()
                recommendations.append(f"CREATE INDEX idx_{table}_{on_clause} ON {table}({on_clause})")
        
        return recommendations
    
    def cache_query_result(self, query: str, result: Any, ttl: int = 300):
        """Cache query result"""
        query_hash = hash(query)
        self.query_cache[query_hash] = {
            "result": result,
            "expires_at": time.time() + ttl
        }
    
    def get_cached_query_result(self, query: str) -> Optional[Any]:
        """Get cached query result"""
        query_hash = hash(query)
        if query_hash in self.query_cache:
            cached = self.query_cache[query_hash]
            if time.time() < cached["expires_at"]:
                return cached["result"]
            else:
                del self.query_cache[query_hash]
        return None


class DatabaseShardingStrategy:
    """Database sharding strategy (if needed)"""
    
    def __init__(self):
        self.shard_count = 1
        self.shard_key = None
    
    def get_shard(self, key: str) -> int:
        """Determine shard for given key"""
        if self.shard_count == 1:
            return 0
        
        # Simple hash-based sharding
        return hash(key) % self.shard_count
    
    def configure_sharding(self, shard_count: int, shard_key: str):
        """Configure sharding strategy"""
        self.shard_count = shard_count
        self.shard_key = shard_key


# Singleton instances
connection_pool = DatabaseConnectionPool()
query_optimizer = QueryOptimizer()
sharding_strategy = DatabaseShardingStrategy()
