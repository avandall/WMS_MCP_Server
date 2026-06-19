"""Security metrics dashboard for WMS MCP Server"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict


class SecurityMetricsDashboard:
    """Security metrics dashboard for monitoring security posture"""
    
    def __init__(self):
        self.metrics = {
            "authentication": {
                "total_attempts": 0,
                "successful_auths": 0,
                "failed_auths": 0,
                "rate_limit_violations": 0
            },
            "authorization": {
                "total_requests": 0,
                "authorized_requests": 0,
                "unauthorized_requests": 0
            },
            "data_protection": {
                "encrypted_operations": 0,
                "pii_masked": 0,
                "gdpr_requests": 0
            },
            "intrusion_detection": {
                "suspicious_activities": 0,
                "blocked_ips": 0,
                "failed_login_attempts": 0
            },
            "compliance": {
                "audit_logs": 0,
                "consent_records": 0,
                "data_deletion_requests": 0
            }
        }
        
        self.time_series_data = defaultdict(list)
    
    def increment_metric(self, category: str, metric_name: str):
        """Increment a specific metric"""
        if category in self.metrics and metric_name in self.metrics[category]:
            self.metrics[category][metric_name] += 1
    
    def record_time_series(self, metric_name: str, value: float):
        """Record time series data for trending"""
        timestamp = datetime.utcnow().isoformat()
        self.time_series_data[metric_name].append({
            "timestamp": timestamp,
            "value": value
        })
        
        # Keep only last 1000 data points
        if len(self.time_series_data[metric_name]) > 1000:
            self.time_series_data[metric_name] = self.time_series_data[metric_name][-1000:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        return self.metrics.copy()
    
    def get_time_series(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get time series data for a metric"""
        if metric_name not in self.time_series_data:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        cutoff_timestamp = cutoff_time.isoformat()
        
        return [
            data_point for data_point in self.time_series_data[metric_name]
            if data_point["timestamp"] >= cutoff_timestamp
        ]
    
    def calculate_security_score(self) -> float:
        """Calculate overall security score (0-100)"""
        total_metrics = 0
        healthy_metrics = 0
        
        for category, metrics in self.metrics.items():
            for metric_name, value in metrics.items():
                total_metrics += 1
                
                # Define health thresholds
                if "failed" in metric_name or "unauthorized" in metric_name or "suspicious" in metric_name:
                    if value == 0:
                        healthy_metrics += 1
                else:
                    if value > 0:
                        healthy_metrics += 1
        
        if total_metrics == 0:
            return 100.0
        
        return (healthy_metrics / total_metrics) * 100
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data"""
        return {
            "security_score": self.calculate_security_score(),
            "metrics": self.get_metrics(),
            "timestamp": datetime.utcnow().isoformat(),
            "summary": self._generate_summary()
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary of security posture"""
        return {
            "total_security_events": sum(
                self.metrics["authentication"]["failed_auths"] +
                self.metrics["intrusion_detection"]["suspicious_activities"]
            ),
            "authentication_success_rate": self._calculate_success_rate(
                self.metrics["authentication"]["successful_auths"],
                self.metrics["authentication"]["total_attempts"]
            ),
            "authorization_success_rate": self._calculate_success_rate(
                self.metrics["authorization"]["authorized_requests"],
                self.metrics["authorization"]["total_requests"]
            )
        }
    
    def _calculate_success_rate(self, successes: int, total: int) -> float:
        """Calculate success rate percentage"""
        if total == 0:
            return 100.0
        return (successes / total) * 100


# Singleton instance
security_dashboard = SecurityMetricsDashboard()
