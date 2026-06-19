"""Rate limiting middleware for WMS MCP Server"""

import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict
from fastapi import HTTPException, status


class RateLimiter:
    """Rate limiter using token bucket algorithm"""
    
    def __init__(self, rate: int, burst: int):
        self.rate = rate  # tokens per second
        self.burst = burst  # maximum burst size
        self.tokens: Dict[str, float] = defaultdict(lambda: burst)
        self.last_update: Dict[str, float] = defaultdict(time.time)
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed"""
        now = time.time()
        elapsed = now - self.last_update[key]
        
        # Add tokens based on elapsed time
        self.tokens[key] = min(self.burst, self.tokens[key] + elapsed * self.rate)
        self.last_update[key] = now
        
        if self.tokens[key] >= 1:
            self.tokens[key] -= 1
            return True
        
        return False


class RateLimitingMiddleware:
    """Rate limiting middleware for per-tool, per-user, and global rate limiting"""
    
    def __init__(self):
        # Per-tool rate limits
        self.tool_rate_limits = {
            "check_stock_availability": RateLimiter(rate=100, burst=10),
            "update_inventory_quantity": RateLimiter(rate=50, burst=5),
            "get_order_status_details": RateLimiter(rate=100, burst=10),
            "generate_picking_route": RateLimiter(rate=50, burst=5),
            "create_shipping_label": RateLimiter(rate=20, burst=2),
        }
        
        # Per-user rate limits
        self.user_rate_limits: Dict[str, RateLimiter] = {}
        
        # Global rate limit
        self.global_rate_limiter = RateLimiter(rate=1000, burst=100)
        
        # Alert thresholds
        self.alert_thresholds = {
            "tool": 0.8,  # Alert when 80% of rate limit is reached
            "user": 0.8,
            "global": 0.8
        }
    
    async def check_rate_limit(
        self,
        tool_name: str,
        user_id: str,
        api_key: str
    ) -> bool:
        """Check if request is allowed based on rate limits"""
        
        # Check global rate limit
        if not self.global_rate_limiter.is_allowed("global"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Global rate limit exceeded"
            )
        
        # Check per-tool rate limit
        if tool_name in self.tool_rate_limits:
            tool_limiter = self.tool_rate_limits[tool_name]
            if not tool_limiter.is_allowed(tool_name):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for tool: {tool_name}"
                )
        
        # Check per-user rate limit
        if user_id not in self.user_rate_limits:
            self.user_rate_limits[user_id] = RateLimiter(rate=100, burst=10)
        
        user_limiter = self.user_rate_limits[user_id]
        if not user_limiter.is_allowed(user_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for user: {user_id}"
            )
        
        return True
    
    def get_rate_limit_status(self, tool_name: str, user_id: str) -> Dict[str, any]:
        """Get current rate limit status"""
        status = {
            "global_tokens": self.global_rate_limiter.tokens.get("global", 0),
            "global_burst": self.global_rate_limiter.burst,
            "tool_tokens": 0,
            "tool_burst": 0,
            "user_tokens": 0,
            "user_burst": 0
        }
        
        if tool_name in self.tool_rate_limits:
            tool_limiter = self.tool_rate_limits[tool_name]
            status["tool_tokens"] = tool_limiter.tokens.get(tool_name, 0)
            status["tool_burst"] = tool_limiter.burst
        
        if user_id in self.user_rate_limits:
            user_limiter = self.user_rate_limits[user_id]
            status["user_tokens"] = user_limiter.tokens.get(user_id, 0)
            status["user_burst"] = user_limiter.burst
        
        return status


# Singleton instance
rate_limiting_middleware = RateLimitingMiddleware()
