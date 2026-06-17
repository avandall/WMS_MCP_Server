"""Redis client for caching and distributed locks"""

from typing import Optional, Any, Dict
import logging
import redis.asyncio as redis
from app.config import Config
import json

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for caching and distributed operations"""
    
    def __init__(self, config: Config):
        """
        Initialize Redis client
        
        Args:
            config: Application configuration
        """
        self.config = config
        self._client: Optional[redis.Redis] = None
        
    async def connect(self) -> None:
        """Establish Redis connection"""
        try:
            self._client = await redis.from_url(
                self.config.REDIS_URL,
                max_connections=self.config.REDIS_POOL_SIZE,
                decode_responses=True
            )
            await self._client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to establish Redis connection: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis
        
        Args:
            key: Redis key
            
        Returns:
            Value or None if not found
        """
        if not self._client:
            await self.connect()
        return await self._client.get(key)
    
    async def set(
        self, 
        key: str, 
        value: str, 
        expire: Optional[int] = None
    ) -> bool:
        """
        Set value in Redis
        
        Args:
            key: Redis key
            value: Value to set
            expire: Optional expiration time in seconds
            
        Returns:
            bool: True if successful
        """
        if not self._client:
            await self.connect()
        return await self._client.set(key, value, ex=expire)
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis
        
        Args:
            key: Redis key
            
        Returns:
            bool: True if key was deleted
        """
        if not self._client:
            await self.connect()
        return await self._client.delete(key) > 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis
        
        Args:
            key: Redis key
            
        Returns:
            bool: True if key exists
        """
        if not self._client:
            await self.connect()
        return await self._client.exists(key) > 0
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get JSON value from Redis
        
        Args:
            key: Redis key
            
        Returns:
            Dict or None if not found
        """
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON for key: {key}")
        return None
    
    async def set_json(
        self, 
        key: str, 
        value: Dict[str, Any], 
        expire: Optional[int] = None
    ) -> bool:
        """
        Set JSON value in Redis
        
        Args:
            key: Redis key
            value: Dict to store
            expire: Optional expiration time in seconds
            
        Returns:
            bool: True if successful
        """
        try:
            json_value = json.dumps(value)
            return await self.set(key, json_value, expire)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to encode JSON for key {key}: {e}")
            return False
    
    # Distributed Lock methods
    async def acquire_lock(
        self, 
        lock_key: str, 
        lock_value: str, 
        expire: int = 30
    ) -> bool:
        """
        Acquire a distributed lock
        
        Args:
            lock_key: Lock key (e.g., "lock:sku:SKU-123")
            lock_value: Unique lock value
            expire: Lock expiration in seconds
            
        Returns:
            bool: True if lock acquired
        """
        if not self._client:
            await self.connect()
            
        # Use SET NX EX for atomic lock acquisition
        result = await self._client.set(
            lock_key, 
            lock_value, 
            nx=True, 
            ex=expire
        )
        return result is not None
    
    async def release_lock(self, lock_key: str, lock_value: str) -> bool:
        """
        Release a distributed lock (only if we own it)
        
        Args:
            lock_key: Lock key
            lock_value: Unique lock value
            
        Returns:
            bool: True if lock was released
        """
        if not self._client:
            await self.connect()
            
        # Lua script to ensure we only release our own lock
        lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
        """
        result = await self._client.eval(
            lua_script, 
            1, 
            lock_key, 
            lock_value
        )
        return result == 1
    
    async def check_lock(self, lock_key: str) -> Optional[Dict[str, Any]]:
        """
        Check if a lock exists and get its info
        
        Args:
            lock_key: Lock key to check
            
        Returns:
            Dict with lock info or None if not locked
        """
        if not self._client:
            await self.connect()
            
        lock_value = await self.get(lock_key)
        if lock_value:
            ttl = await self._client.ttl(lock_key)
            return {
                "lock_key": lock_key,
                "lock_value": lock_value,
                "ttl_seconds": ttl
            }
        return None
    
    async def get_all_locks(self, pattern: str = "lock:*") -> list:
        """
        Get all locks matching a pattern
        
        Args:
            pattern: Lock key pattern (default: "lock:*")
            
        Returns:
            List of lock info dicts
        """
        if not self._client:
            await self.connect()
            
        locks = []
        keys = []
        async for key in self._client.scan_iter(match=pattern):
            keys.append(key)
            
        for key in keys:
            lock_info = await self.check_lock(key)
            if lock_info:
                locks.append(lock_info)
                
        return locks
    
    # Cache methods
    async def cache_get(
        self, 
        key: str, 
        default: Optional[Any] = None
    ) -> Optional[Any]:
        """
        Get value from cache with JSON decoding
        
        Args:
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        if not self.config.CACHE_ENABLED:
            return default
            
        value = await self.get_json(key)
        return value if value is not None else default
    
    async def cache_set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with JSON encoding
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if not provided)
            
        Returns:
            bool: True if successful
        """
        if not self.config.CACHE_ENABLED:
            return False
            
        if ttl is None:
            ttl = self.config.CACHE_TTL_SECONDS
            
        return await self.set_json(key, value, ttl)
    
    async def cache_delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if deleted
        """
        return await self.delete(key)
    
    async def cache_clear_pattern(self, pattern: str) -> int:
        """
        Clear all cache keys matching a pattern
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            Number of keys deleted
        """
        if not self._client:
            await self.connect()
            
        count = 0
        async for key in self._client.scan_iter(match=pattern):
            await self.delete(key)
            count += 1
            
        return count
