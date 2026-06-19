"""Multi-level caching strategy for WMS MCP Server"""

import time
import hashlib
import json
from typing import Any, Optional, Dict, List
from functools import wraps
from collections import defaultdict


class CacheLevel:
    """Base class for cache levels"""
    
    def __init__(self, name: str, ttl: int = 300):
        self.name = name
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            self.metrics["misses"] += 1
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if time.time() > entry["expires_at"]:
            del self.cache[key]
            self.metrics["misses"] += 1
            self.metrics["evictions"] += 1
            return None
        
        self.metrics["hits"] += 1
        return entry["value"]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        cache_ttl = ttl if ttl is not None else self.ttl
        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + cache_ttl,
            "created_at": time.time()
        }
    
    def delete(self, key: str):
        """Delete value from cache"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = (self.metrics["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.metrics,
            "hit_rate": hit_rate,
            "size": len(self.cache)
        }


class InMemoryCache(CacheLevel):
    """In-memory cache (L1 cache)"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 60):
        super().__init__("L1_InMemory", ttl)
        self.max_size = max_size
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value with size limit"""
        # Evict oldest entries if at capacity
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["created_at"])
            del self.cache[oldest_key]
            self.metrics["evictions"] += 1
        
        super().set(key, value, ttl)


class MultiLevelCache:
    """Multi-level cache manager"""
    
    def __init__(self):
        # L1: In-memory cache (fastest, smallest)
        self.l1_cache = InMemoryCache(max_size=1000, ttl=60)
        
        # L2: Redis cache (medium speed, medium size)
        self.l2_cache = None  # Will be initialized with Redis client
        
        # L3: Database cache (slowest, largest)
        self.l3_cache = None  # Will be initialized with database client
        
        self.cache_warming_enabled = True
        self.cache_invalidation_policies = {
            "time_based": True,
            "event_based": True,
            "manual": True
        }
    
    def initialize_l2_cache(self, redis_client):
        """Initialize L2 cache with Redis client"""
        self.l2_cache = redis_client
    
    def initialize_l3_cache(self, db_client):
        """Initialize L3 cache with database client"""
        self.l3_cache = db_client
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from multi-level cache"""
        # Try L1 cache first
        value = self.l1_cache.get(key)
        if value is not None:
            return value
        
        # Try L2 cache
        if self.l2_cache:
            value = await self.l2_cache.cache_get(key)
            if value is not None:
                # Promote to L1 cache
                self.l1_cache.set(key, value)
                return value
        
        # Try L3 cache
        if self.l3_cache:
            value = await self._get_from_l3_cache(key)
            if value is not None:
                # Promote to L2 and L1 caches
                if self.l2_cache:
                    await self.l2_cache.cache_set(key, value)
                self.l1_cache.set(key, value)
                return value
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in multi-level cache"""
        # Set in all cache levels
        self.l1_cache.set(key, value, ttl)
        
        if self.l2_cache:
            await self.l2_cache.cache_set(key, value, ttl)
        
        if self.l3_cache:
            await self._set_in_l3_cache(key, value, ttl)
    
    def delete(self, key: str):
        """Delete value from all cache levels"""
        self.l1_cache.delete(key)
        
        if self.l2_cache:
            await self.l2_cache.cache_delete(key)
        
        if self.l3_cache:
            await self._delete_from_l3_cache(key)
    
    async def _get_from_l3_cache(self, key: str) -> Optional[Any]:
        """Get value from L3 cache (database)"""
        # Implementation would query database cache table
        return None
    
    async def _set_in_l3_cache(self, key: str, value: Any, ttl: Optional[int]):
        """Set value in L3 cache (database)"""
        # Implementation would insert/update database cache table
        pass
    
    async def _delete_from_l3_cache(self, key: str):
        """Delete value from L3 cache (database)"""
        # Implementation would delete from database cache table
        pass
    
    def warm_cache(self, keys: List[str], data_loader):
        """Warm cache with frequently accessed data"""
        if not self.cache_warming_enabled:
            return
        
        for key in keys:
            value = data_loader(key)
            if value is not None:
                self.set(key, value)
    
    def invalidate_cache(self, pattern: str = None):
        """Invalidate cache based on pattern or all"""
        if pattern:
            # Pattern-based invalidation
            keys_to_delete = [k for k in self.l1_cache.cache.keys() if pattern in k]
            for key in keys_to_delete:
                self.delete(key)
        else:
            # Clear all caches
            self.l1_cache.clear()
            if self.l2_cache:
                # Clear Redis cache
                pass
            if self.l3_cache:
                # Clear database cache
                pass
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics from all cache levels"""
        return {
            "l1_cache": self.l1_cache.get_metrics(),
            "l2_cache": self.l2_cache.get_metrics() if self.l2_cache else None,
            "l3_cache": self.l3_cache.get_metrics() if self.l3_cache else None
        }


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a cache key from function arguments"""
    key_parts = [prefix]
    
    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(hashlib.md5(json.dumps(arg, sort_keys=True).encode()).hexdigest())
    
    # Add keyword arguments
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    return ":".join(key_parts)


def cached(ttl: int = 300, prefix: str = None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = generate_cache_key(prefix or func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_value = multi_level_cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            multi_level_cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# Singleton instance
multi_level_cache = MultiLevelCache()
