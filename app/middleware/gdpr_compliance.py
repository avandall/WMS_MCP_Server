"""GDPR compliance features for WMS MCP Server"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path


class GDPRCompliance:
    """GDPR compliance handler for data protection and privacy"""
    
    def __init__(self):
        self.consent_records = {}
        self.data_retention_days = int(os.getenv("DATA_RETENTION_DAYS", "365"))
        self.data_directory = Path(os.getenv("DATA_DIRECTORY", "./data"))
        self.data_directory.mkdir(exist_ok=True)
    
    def record_consent(self, user_id: str, consent_data: Dict[str, Any]):
        """Record user consent for data processing"""
        consent_record = {
            "user_id": user_id,
            "consent_given": consent_data.get("consent_given", False),
            "consent_type": consent_data.get("consent_type", "data_processing"),
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": consent_data.get("ip_address"),
            "user_agent": consent_data.get("user_agent")
        }
        
        if user_id not in self.consent_records:
            self.consent_records[user_id] = []
        
        self.consent_records[user_id].append(consent_record)
    
    def check_consent(self, user_id: str, consent_type: str = "data_processing") -> bool:
        """Check if user has given consent for data processing"""
        if user_id not in self.consent_records:
            return False
        
        user_consents = self.consent_records[user_id]
        for consent in reversed(user_consents):
            if consent["consent_type"] == consent_type:
                return consent["consent_given"]
        
        return False
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export all user data for GDPR right to data portability"""
        user_data = {
            "user_id": user_id,
            "export_timestamp": datetime.utcnow().isoformat(),
            "consent_records": self.consent_records.get(user_id, []),
            "additional_data": {}
        }
        
        # Load additional user data from storage
        user_data_file = self.data_directory / f"user_{user_id}.json"
        if user_data_file.exists():
            with open(user_data_file) as f:
                user_data["additional_data"] = json.load(f)
        
        return user_data
    
    def delete_user_data(self, user_id: str) -> bool:
        """Delete all user data for GDPR right to be forgotten"""
        try:
            # Delete consent records
            if user_id in self.consent_records:
                del self.consent_records[user_id]
            
            # Delete user data file
            user_data_file = self.data_directory / f"user_{user_id}.json"
            if user_data_file.exists():
                user_data_file.unlink()
            
            return True
        except Exception as e:
            print(f"Failed to delete user data: {e}")
            return False
    
    def anonymize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize data for privacy protection"""
        anonymized = data.copy()
        
        # Remove or hash identifying fields
        sensitive_fields = ["email", "phone", "name", "address", "ssn"]
        
        for field in sensitive_fields:
            if field in anonymized:
                anonymized[field] = "***REDACTED***"
        
        return anonymized
    
    def check_data_retention(self, data_timestamp: str) -> bool:
        """Check if data should be retained based on retention policy"""
        try:
            data_date = datetime.fromisoformat(data_timestamp)
            current_date = datetime.utcnow()
            days_old = (current_date - data_date).days
            return days_old <= self.data_retention_days
        except Exception:
            return False
    
    def log_data_access(self, user_id: str, access_type: str, purpose: str):
        """Log data access for GDPR accountability"""
        access_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "access_type": access_type,
            "purpose": purpose
        }
        
        log_file = self.data_directory / "data_access_log.json"
        logs = []
        
        if log_file.exists():
            with open(log_file) as f:
                logs = json.load(f)
        
        logs.append(access_log)
        
        with open(log_file, "w") as f:
            json.dump(logs, f, indent=2)


# Singleton instance
gdpr_compliance = GDPRCompliance()
