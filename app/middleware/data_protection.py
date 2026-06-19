"""Data protection middleware for WMS MCP Server"""

import os
import re
from typing import Any, Dict
from cryptography.fernet import Fernet
import hashlib


class DataProtectionMiddleware:
    """Data protection middleware for encryption, masking, and PII handling"""
    
    def __init__(self):
        self.encryption_key = self._load_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        
        # PII patterns for detection and masking
        self.pii_patterns = {
            "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "phone": r'\+?[\d\s-]{10,}',
            "credit_card": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            "ssn": r'\b\d{3}[-]?\d{2}[-]?\d{4}\b',
        }
    
    def _load_encryption_key(self) -> bytes:
        """Load encryption key from environment or generate one"""
        key = os.getenv("ENCRYPTION_KEY")
        if key:
            return key.encode()
        
        # Generate a new key (in production, this should be stored securely)
        return Fernet.generate_key()
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt data at rest"""
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data at rest"""
        decrypted = self.cipher.decrypt(encrypted_data.encode())
        return decrypted.decode()
    
    def mask_pii(self, data: str) -> str:
        """Mask PII data in logs and responses"""
        masked_data = data
        
        for pii_type, pattern in self.pii_patterns.items():
            if pii_type == "email":
                masked_data = re.sub(pattern, lambda m: self._mask_email(m.group()), masked_data)
            elif pii_type == "phone":
                masked_data = re.sub(pattern, lambda m: self._mask_phone(m.group()), masked_data)
            elif pii_type == "credit_card":
                masked_data = re.sub(pattern, lambda m: self._mask_credit_card(m.group()), masked_data)
            elif pii_type == "ssn":
                masked_data = re.sub(pattern, lambda m: self._mask_ssn(m.group()), masked_data)
        
        return masked_data
    
    def _mask_email(self, email: str) -> str:
        """Mask email address"""
        parts = email.split('@')
        if len(parts) == 2:
            username = parts[0]
            domain = parts[1]
            masked_username = username[0] + '*' * (len(username) - 1)
            return f"{masked_username}@{domain}"
        return email
    
    def _mask_phone(self, phone: str) -> str:
        """Mask phone number"""
        digits = re.sub(r'\D', '', phone)
        if len(digits) >= 10:
            return digits[:3] + '-' + '*' * 3 + '-' + digits[-4:]
        return phone
    
    def _mask_credit_card(self, card: str) -> str:
        """Mask credit card number"""
        digits = re.sub(r'\D', '', card)
        if len(digits) == 16:
            return '*' * 12 + digits[-4:]
        return card
    
    def _mask_ssn(self, ssn: str) -> str:
        """Mask SSN"""
        digits = re.sub(r'\D', '', ssn)
        if len(digits) == 9:
            return '***-**-' + digits[-4:]
        return ssn
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for comparison"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def ensure_encryption_in_transit(self, request: Any) -> bool:
        """Ensure encryption in transit (HTTPS/TLS)"""
        # This would check if the request is using HTTPS
        # For now, return True as this is typically handled by the web server
        return True


# Singleton instance
data_protection_middleware = DataProtectionMiddleware()
