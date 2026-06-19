"""JWT token authentication for WMS MCP Server"""

import os
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException, status


class JWTAuth:
    """JWT token authentication handler"""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.token_expiry = int(os.getenv("JWT_TOKEN_EXPIRY", "3600"))  # 1 hour default
    
    def generate_token(self, user_id: str, roles: list, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """Generate a JWT token"""
        payload = {
            "user_id": user_id,
            "roles": roles,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=self.token_expiry)
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token and return the payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def refresh_token(self, token: str) -> str:
        """Refresh a JWT token"""
        payload = self.validate_token(token)
        user_id = payload.get("user_id")
        roles = payload.get("roles", [])
        
        # Generate new token with same claims
        return self.generate_token(user_id, roles)


# Singleton instance
jwt_auth = JWTAuth()
