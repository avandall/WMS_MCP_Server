"""Connection pool manager for database and external services"""

import logging
from typing import Optional
from contextlib import asynccontextmanager
from app.clients.database_client import DatabaseClient
from app.clients.redis_client import RedisClient
from app.clients.queue_client import QueueClient
from app.config import Config

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages connection pools for all external services"""
    
    def __init__(self, config: Config):
        """Initialize connection manager"""
        self.config = config
        self._db: Optional[DatabaseClient] = None
        self._redis: Optional[RedisClient] = None
        self._queue: Optional[QueueClient] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize all connection pools"""
        if self._initialized:
            logger.warning("ConnectionManager already initialized")
            return
        
        try:
            logger.info("Initializing connection pools...")
            
            # Initialize database client
            self._db = DatabaseClient(self.config)
            await self._db.connect()
            logger.info("Database connection pool established")
            
            # Initialize Redis client
            self._redis = RedisClient(self.config)
            await self._redis.connect()
            logger.info("Redis connection pool established")
            
            # Initialize queue client
            self._queue = QueueClient(self.config)
            await self._queue.connect()
            logger.info("Queue connection pool established")
            
            self._initialized = True
            logger.info("All connection pools initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pools: {e}", exc_info=True)
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """Close all connection pools"""
        logger.info("Cleaning up connection pools...")
        
        if self._db:
            try:
                await self._db.disconnect()
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
        
        if self._redis:
            try:
                await self._redis.disconnect()
                logger.info("Redis connection pool closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
        
        if self._queue:
            try:
                await self._queue.disconnect()
                logger.info("Queue connection pool closed")
            except Exception as e:
                logger.error(f"Error closing queue connection: {e}")
        
        self._initialized = False
    
    @property
    def db(self) -> DatabaseClient:
        """Get database client"""
        if not self._initialized or not self._db:
            raise RuntimeError("ConnectionManager not initialized")
        return self._db
    
    @property
    def redis(self) -> RedisClient:
        """Get Redis client"""
        if not self._initialized or not self._redis:
            raise RuntimeError("ConnectionManager not initialized")
        return self._redis
    
    @property
    def queue(self) -> QueueClient:
        """Get queue client"""
        if not self._initialized or not self._queue:
            raise RuntimeError("ConnectionManager not initialized")
        return self._queue
    
    @asynccontextmanager
    async def get_db_connection(self):
        """Get database connection from pool"""
        async with self.db.get_connection() as conn:
            yield conn
    
    def health_check(self) -> dict:
        """Check health of all connections"""
        health = {
            "initialized": self._initialized,
            "database": "unknown",
            "redis": "unknown",
            "queue": "unknown"
        }
        
        if not self._initialized:
            return health
        
        # Check database health
        try:
            # Simple health check would go here
            health["database"] = "healthy"
        except Exception as e:
            health["database"] = f"unhealthy: {str(e)}"
        
        # Check Redis health
        try:
            if self._redis and hasattr(self._redis, '_client'):
                health["redis"] = "healthy"
            else:
                health["redis"] = "not connected"
        except Exception as e:
            health["redis"] = f"unhealthy: {str(e)}"
        
        # Check queue health
        try:
            if self._queue and hasattr(self._queue, '_connection'):
                health["queue"] = "healthy"
            else:
                health["queue"] = "not connected"
        except Exception as e:
            health["queue"] = f"unhealthy: {str(e)}"
        
        return health


# Global connection manager instance
_global_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager(config: Config) -> ConnectionManager:
    """Get or create global connection manager"""
    global _global_connection_manager
    if _global_connection_manager is None:
        _global_connection_manager = ConnectionManager(config)
    return _global_connection_manager
