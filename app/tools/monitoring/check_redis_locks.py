"""Check Redis locks tool"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.redis_client import RedisClient
from app.utils.error_handlers import handle_tool_error


class CheckRedisLocksInput(BaseModel):
    """Input schema for check_redis_locks"""
    resource_key: str = Field(..., description="Resource key to check (e.g., lock:sku:SKU-1060-6GB or lock:order:123)")


class CheckRedisLocks(BaseTool):
    """Check distributed locks on Redis"""
    
    name = "check_redis_locks"
    description = "Check distributed locks on Redis to find causes of API hangs or race conditions"
    
    def __init__(self, config):
        super().__init__(config)
        self.redis = RedisClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "resource_key": {
                    "type": "string",
                    "description": "Resource key to check (e.g., lock:sku:SKU-1060-6GB or lock:order:123)"
                }
            },
            "required": ["resource_key"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = CheckRedisLocksInput(**kwargs)
            
            # Connect to Redis
            await self.redis.connect()
            
            # Check specific lock
            lock_info = await self.redis.check_lock(input_data.resource_key)
            
            # Also check for related locks if it's a pattern
            pattern = input_data.resource_key.replace(':', ':*') if ':' in input_data.resource_key else f"*{input_data.resource_key}*"
            all_locks = await self.redis.get_all_locks(pattern)
            
            # Close connection
            await self.redis.disconnect()
            
            return ToolResult(
                success=True,
                data={
                    "requested_key": input_data.resource_key,
                    "specific_lock": lock_info,
                    "related_locks": all_locks,
                    "total_related_locks": len(all_locks),
                    "analysis": self._analyze_locks(lock_info, all_locks)
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
    
    def _analyze_locks(self, specific_lock: Dict[str, Any], all_locks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze lock status and provide insights"""
        analysis = {
            "has_active_lock": False,
            "lock_age_seconds": None,
            "potential_deadlock": False,
            "recommendation": "No issues detected"
        }
        
        if specific_lock:
            analysis["has_active_lock"] = True
            ttl = specific_lock.get("ttl_seconds", 0)
            if ttl > 0:
                analysis["lock_age_seconds"] = 30 - ttl  # Assuming 30s default expiration
            else:
                analysis["lock_age_seconds"] = "unknown (no TTL)"
        
        # Check for potential deadlock (multiple locks on same resource)
        if len(all_locks) > 1:
            analysis["potential_deadlock"] = True
            analysis["recommendation"] = "Multiple locks detected - possible deadlock condition"
        
        # Check for stale locks (no TTL or very old)
        for lock in all_locks:
            ttl = lock.get("ttl_seconds", -1)
            if ttl == -1 or ttl == -2:  # No TTL or key doesn't exist
                analysis["recommendation"] = "Stale lock detected - consider manual cleanup"
                break
        
        return analysis
