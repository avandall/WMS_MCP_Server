"""Service-to-service authentication for WMS MCP Server"""

import os
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException, status


class ServiceAuth:
    """Service-to-service authentication using mutual TLS or API keys"""
    
    def __init__(self):
        self.service_keys = self._load_service_keys()
    
    def _load_service_keys(self) -> Dict[str, Dict[str, Any]]:
        """Load service keys from environment"""
        service_keys = {}
        
        # Load service keys from environment
        services = ["WMS_CORE", "ORDER_SERVICE", "INVENTORY_SERVICE", "SHIPPING_SERVICE"]
        
        for service in services:
            key = os.getenv(f"{service}_API_KEY")
            if key:
                service_keys[key] = {
                    "service_name": service,
                    "active": True,
                    "permissions": ["read", "write"]
                }
        
        return service_keys
    
    def validate_service_key(self, service_key: str) -> Dict[str, Any]:
        """Validate service key and return service context"""
        if not service_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Service key is required"
            )
        
        if service_key not in self.service_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid service key"
            )
        
        key_data = self.service_keys[service_key]
        
        if not key_data.get("active", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Service key is inactive"
            )
        
        return key_data
    
    def generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for service-to-service communication"""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def validate_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Validate HMAC signature"""
        expected_signature = self.generate_signature(payload, secret)
        return hmac.compare_digest(expected_signature, signature)


# Singleton instance
service_auth = ServiceAuth()
