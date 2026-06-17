"""Database client abstraction for WMS MCP Server"""

from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
import logging
import asyncpg
from app.config import Config

logger = logging.getLogger(__name__)


class DatabaseClient:
    """PostgreSQL database client with connection pooling"""
    
    def __init__(self, config: Config):
        """
        Initialize database client
        
        Args:
            config: Application configuration
        """
        self.config = config
        self._pool: Optional[asyncpg.Pool] = None
        
    async def connect(self) -> None:
        """Establish database connection pool"""
        try:
            self._pool = await asyncpg.create_pool(
                self.config.DATABASE_URL,
                min_size=1,
                max_size=self.config.DATABASE_POOL_SIZE,
                max_overflow=self.config.DATABASE_MAX_OVERFLOW,
                command_timeout=30
            )
            logger.info("Database connection pool established")
        except Exception as e:
            logger.error(f"Failed to establish database connection: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close database connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """
        Get a database connection from the pool
        
        Yields:
            asyncpg.Connection: Database connection
        """
        if not self._pool:
            await self.connect()
            
        async with self._pool.acquire() as conn:
            yield conn
    
    async def execute(self, query: str, *args, **kwargs) -> str:
        """
        Execute a SQL query (INSERT, UPDATE, DELETE)
        
        Args:
            query: SQL query string
            *args: Query parameters
            **kwargs: Additional query options
            
        Returns:
            str: Execution status
        """
        async with self.get_connection() as conn:
            return await conn.execute(query, *args, **kwargs)
    
    async def fetch_one(self, query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row from database
        
        Args:
            query: SQL query string
            *args: Query parameters
            **kwargs: Additional query options
            
        Returns:
            Dict containing row data or None
        """
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *args, **kwargs)
            return dict(row) if row else None
    
    async def fetch_many(self, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch multiple rows from database
        
        Args:
            query: SQL query string
            *args: Query parameters
            **kwargs: Additional query options
            
        Returns:
            List of dicts containing row data
        """
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args, **kwargs)
            return [dict(row) for row in rows]
    
    async def fetch_val(self, query: str, *args, column: int = 0, **kwargs) -> Any:
        """
        Fetch a single value from database
        
        Args:
            query: SQL query string
            *args: Query parameters
            column: Column index to fetch
            **kwargs: Additional query options
            
        Returns:
            Single value or None
        """
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args, column=column, **kwargs)
    
    async def execute_transaction(self, queries: List[Dict[str, Any]]) -> bool:
        """
        Execute multiple queries in a transaction
        
        Args:
            queries: List of dicts with 'query' and 'params' keys
            
        Returns:
            bool: True if transaction succeeded
        """
        async with self.get_connection() as conn:
            async with conn.transaction():
                for query_item in queries:
                    query = query_item['query']
                    params = query_item.get('params', [])
                    await conn.execute(query, *params)
        return True
    
    # Inventory-specific methods
    async def get_stock_info(self, sku_code: str, warehouse_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get stock information for a SKU
        
        Args:
            sku_code: SKU code
            warehouse_id: Optional warehouse ID filter
            
        Returns:
            Stock information dict
        """
        query = """
            SELECT 
                sku_code,
                warehouse_id,
                physical_qty,
                available_qty,
                reserved_qty,
                location_code,
                last_updated
            FROM inventory_stock
            WHERE sku_code = $1
        """
        params = [sku_code]
        
        if warehouse_id:
            query += " AND warehouse_id = $2"
            params.append(warehouse_id)
            
        return await self.fetch_one(query, *params)
    
    async def update_stock_quantity(
        self, 
        sku_code: str, 
        location_code: str, 
        quantity: int,
        warehouse_id: Optional[int] = None
    ) -> bool:
        """
        Update stock quantity for a SKU at a location
        
        Args:
            sku_code: SKU code
            location_code: Location code
            quantity: Quantity change (positive or negative)
            warehouse_id: Optional warehouse ID
            
        Returns:
            bool: True if update succeeded
        """
        query = """
            UPDATE inventory_stock
            SET 
                physical_qty = physical_qty + $1,
                available_qty = available_qty + $1,
                last_updated = NOW()
            WHERE sku_code = $2 AND location_code = $3
        """
        params = [quantity, sku_code, location_code]
        
        if warehouse_id:
            query += " AND warehouse_id = $4"
            params.append(warehouse_id)
            
        result = await self.execute(query, *params)
        return "UPDATE" in result
    
    async def get_shelf_capacity(self, location_code: str) -> Optional[Dict[str, Any]]:
        """
        Get shelf capacity information
        
        Args:
            location_code: Location code
            
        Returns:
            Shelf capacity dict
        """
        query = """
            SELECT 
                location_code,
                zone_id,
                row_id,
                shelf_id,
                max_volume,
                max_weight,
                current_volume,
                current_weight,
                available_volume,
                available_weight
            FROM warehouse_locations
            WHERE location_code = $1
        """
        return await self.fetch_one(query, location_code)
    
    async def get_abc_classification(self, sku_code: str) -> Optional[Dict[str, Any]]:
        """
        Get ABC classification for a SKU
        
        Args:
            sku_code: SKU code
            
        Returns:
            ABC classification dict
        """
        query = """
            SELECT 
                sku_code,
                abc_class,
                turnover_rate,
                annual_demand,
                avg_order_value,
                last_calculated
            FROM abc_analysis
            WHERE sku_code = $1
        """
        return await self.fetch_one(query, sku_code)
    
    async def get_stock_movement_history(
        self, 
        sku_code: str, 
        limit_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get stock movement history for a SKU
        
        Args:
            sku_code: SKU code
            limit_days: Number of days to look back
            
        Returns:
            List of movement records
        """
        query = """
            SELECT 
                movement_id,
                sku_code,
                from_location,
                to_location,
                quantity,
                movement_type,
                reference_id,
                created_at,
                created_by
            FROM stock_movements
            WHERE sku_code = $1
            AND created_at >= NOW() - INTERVAL '1 day' * $2
            ORDER BY created_at DESC
        """
        return await self.fetch_many(query, sku_code, limit_days)
    
    async def get_low_stock_items(self, threshold_qty: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get items with low stock
        
        Args:
            threshold_qty: Optional custom threshold
            
        Returns:
            List of low stock items
        """
        if threshold_qty is None:
            query = """
                SELECT 
                    sku_code,
                    warehouse_id,
                    available_qty,
                    safety_stock,
                    (available_qty - safety_stock) as below_safety_by
                FROM inventory_stock
                WHERE available_qty <= safety_stock
                ORDER BY (available_qty - safety_stock) ASC
            """
            return await self.fetch_many(query)
        else:
            query = """
                SELECT 
                    sku_code,
                    warehouse_id,
                    available_qty,
                    safety_stock,
                    ($1 - available_qty) as below_threshold_by
                FROM inventory_stock
                WHERE available_qty <= $1
                ORDER BY available_qty ASC
            """
            return await self.fetch_many(query, threshold_qty)
