"""Security monitoring middleware for WMS MCP Server"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict, deque


class SecurityEventLogger:
    """Security event logger for tracking security-related events"""
    
    def __init__(self):
        self.logger = logging.getLogger("security")
        self.events = deque(maxlen=1000)  # Keep last 1000 events
    
    def log_event(
        self,
        event_type: str,
        user_id: str,
        details: Dict[str, Any],
        severity: str = "INFO"
    ):
        """Log a security event"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "details": details,
            "severity": severity
        }
        
        self.events.append(event)
        
        log_method = {
            "INFO": self.logger.info,
            "WARNING": self.logger.warning,
            "ERROR": self.logger.error,
            "CRITICAL": self.logger.critical
        }.get(severity, self.logger.info)
        
        log_method(f"{event_type}: {details}")
    
    def get_recent_events(self, limit: int = 100) -> list:
        """Get recent security events"""
        return list(self.events)[-limit:]


class IntrusionDetector:
    """Intrusion detection system for identifying suspicious activity"""
    
    def __init__(self):
        self.failed_attempts: Dict[str, int] = defaultdict(int)
        self.suspicious_ips: set = set()
        self.rate_violations: Dict[str, int] = defaultdict(int)
        
        # Thresholds
        self.max_failed_attempts = 5
        self.max_rate_violations = 10
    
    def check_failed_login(self, user_id: str, ip: str) -> bool:
        """Check if user has too many failed login attempts"""
        self.failed_attempts[user_id] += 1
        
        if self.failed_attempts[user_id] >= self.max_failed_attempts:
            self.suspicious_ips.add(ip)
            return True
        
        return False
    
    def check_rate_violation(self, user_id: str) -> bool:
        """Check if user has too many rate limit violations"""
        self.rate_violations[user_id] += 1
        
        if self.rate_violations[user_id] >= self.max_rate_violations:
            return True
        
        return False
    
    def is_ip_suspicious(self, ip: str) -> bool:
        """Check if IP is flagged as suspicious"""
        return ip in self.suspicious_ips
    
    def reset_failed_attempts(self, user_id: str):
        """Reset failed attempts for user"""
        self.failed_attempts[user_id] = 0


class AuditTrail:
    """Audit trail for sensitive operations"""
    
    def __init__(self):
        self.audit_log = deque(maxlen=1000)
    
    def log_sensitive_operation(
        self,
        operation: str,
        user_id: str,
        resource: str,
        details: Dict[str, Any]
    ):
        """Log a sensitive operation"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "user_id": user_id,
            "resource": resource,
            "details": details
        }
        
        self.audit_log.append(audit_entry)
    
    def get_audit_trail(
        self,
        user_id: Optional[str] = None,
        operation: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """Get audit trail with optional filters"""
        trail = list(self.audit_log)
        
        if user_id:
            trail = [e for e in trail if e["user_id"] == user_id]
        
        if operation:
            trail = [e for e in trail if e["operation"] == operation]
        
        return trail[-limit:]


class SecurityMetrics:
    """Security metrics for dashboard"""
    
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "failed_authentications": 0,
            "rate_limit_violations": 0,
            "suspicious_activities": 0,
            "blocked_ips": 0
        }
    
    def increment_metric(self, metric_name: str):
        """Increment a security metric"""
        if metric_name in self.metrics:
            self.metrics[metric_name] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all security metrics"""
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset all metrics"""
        for key in self.metrics:
            self.metrics[key] = 0


class SecurityMonitoringMiddleware:
    """Security monitoring middleware combining all security monitoring features"""
    
    def __init__(self):
        self.event_logger = SecurityEventLogger()
        self.intrusion_detector = IntrusionDetector()
        self.audit_trail = AuditTrail()
        self.security_metrics = SecurityMetrics()
    
    def log_security_event(
        self,
        event_type: str,
        user_id: str,
        details: Dict[str, Any],
        severity: str = "INFO"
    ):
        """Log a security event"""
        self.event_logger.log_event(event_type, user_id, details, severity)
    
    def check_intrusion(self, user_id: str, ip: str) -> bool:
        """Check for intrusion attempts"""
        return self.intrusion_detector.is_ip_suspicious(ip)
    
    def log_sensitive_operation(
        self,
        operation: str,
        user_id: str,
        resource: str,
        details: Dict[str, Any]
    ):
        """Log a sensitive operation to audit trail"""
        self.audit_trail.log_sensitive_operation(operation, user_id, resource, details)
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get overall security status"""
        return {
            "metrics": self.security_metrics.get_metrics(),
            "recent_events": self.event_logger.get_recent_events(10),
            "suspicious_ips": len(self.intrusion_detector.suspicious_ips),
            "audit_entries": len(self.audit_trail.audit_log)
        }


# Singleton instance
security_monitoring_middleware = SecurityMonitoringMiddleware()
