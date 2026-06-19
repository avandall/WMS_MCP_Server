"""Authentication middleware for WMS MCP Server"""

import os
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader


class AuthenticationMiddleware:
    """Authentication middleware for API key and JWT token validation"""
    
    def __init__(self):
        self.api_keys = self._load_api_keys()
        self.api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
    
    def _load_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """Load API keys from environment or database"""
        api_keys = {}
        
        # Load from environment
        env_api_key = os.getenv("WMS_API_KEY")
        if env_api_key:
            api_keys[env_api_key] = {
                "roles": ["admin"],
                "user_id": "system",
                "active": True
            }
        
        # Additional API keys can be loaded from database
        # This is a placeholder for database integration
        
        return api_keys
    
    async def validate_api_key(self, api_key: Optional[str] = Security(None)) -> Dict[str, Any]:
        """Validate API key and return user context"""
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is required"
            )
        
        if api_key not in self.api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        key_data = self.api_keys[api_key]
        
        if not key_data.get("active", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is inactive"
            )
        
        return key_data
    
    async def check_permission(self, user_context: Dict[str, Any], required_permission: str) -> bool:
        """Check if user has required permission"""
        user_roles = user_context.get("roles", [])
        
        # Admin role has all permissions
        if "admin" in user_roles:
            return True
        
        # Check role-based permissions
        role_permissions = {
            "inventory:read": ["inventory_user", "admin"],
            "inventory:write": ["inventory_admin", "admin"],
            "orders:read": ["order_user", "admin"],
            "orders:write": ["order_admin", "admin"],
            "monitoring:read": ["monitoring_user", "admin"],
            "system:admin": ["admin"]
        }
        
        allowed_roles = role_permissions.get(required_permission, [])
        return any(role in user_roles for role in allowed_roles)


# Singleton instance
auth_middleware = AuthenticationMiddleware()
