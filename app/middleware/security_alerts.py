"""Security alerts configuration for WMS MCP Server"""

import os
import smtplib
from email.mime.text import MIMEText
from typing import Dict, Any, List
from datetime import datetime


class SecurityAlertManager:
    """Security alert manager for configuring and sending security alerts"""
    
    def __init__(self):
        self.alert_channels = self._load_alert_channels()
        self.alert_rules = self._load_alert_rules()
    
    def _load_alert_channels(self) -> Dict[str, Any]:
        """Load alert channel configurations"""
        return {
            "email": {
                "enabled": os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true",
                "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "smtp_user": os.getenv("SMTP_USER"),
                "smtp_password": os.getenv("SMTP_PASSWORD"),
                "recipients": os.getenv("ALERT_RECIPIENTS", "").split(","),
            },
            "webhook": {
                "enabled": os.getenv("ALERT_WEBHOOK_ENABLED", "false").lower() == "true",
                "url": os.getenv("ALERT_WEBHOOK_URL"),
            },
            "slack": {
                "enabled": os.getenv("ALERT_SLACK_ENABLED", "false").lower() == "true",
                "webhook_url": os.getenv("SLACK_WEBHOOK_URL"),
            }
        }
    
    def _load_alert_rules(self) -> Dict[str, Any]:
        """Load alert rules and thresholds"""
        return {
            "failed_auth_threshold": int(os.getenv("FAILED_AUTH_THRESHOLD", "5")),
            "rate_limit_threshold": int(os.getenv("RATE_LIMIT_THRESHOLD", "10")),
            "suspicious_activity_threshold": int(os.getenv("SUSPICIOUS_ACTIVITY_THRESHOLD", "3")),
            "intrusion_detection_threshold": int(os.getenv("INTRUSION_DETECTION_THRESHOLD", "1")),
        }
    
    def send_email_alert(self, subject: str, message: str):
        """Send security alert via email"""
        if not self.alert_channels["email"]["enabled"]:
            return
        
        try:
            msg = MIMEText(message)
            msg["Subject"] = f"[WMS Security Alert] {subject}"
            msg["From"] = self.alert_channels["email"]["smtp_user"]
            msg["To"] = ", ".join(self.alert_channels["email"]["recipients"])
            
            with smtplib.SMTP(
                self.alert_channels["email"]["smtp_server"],
                self.alert_channels["email"]["smtp_port"]
            ) as server:
                server.starttls()
                server.login(
                    self.alert_channels["email"]["smtp_user"],
                    self.alert_channels["email"]["smtp_password"]
                )
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email alert: {e}")
    
    def send_webhook_alert(self, alert_data: Dict[str, Any]):
        """Send security alert via webhook"""
        if not self.alert_channels["webhook"]["enabled"]:
            return
        
        # Implementation would use requests.post to send to webhook
        # This is a placeholder for webhook integration
        pass
    
    def send_slack_alert(self, message: str):
        """Send security alert via Slack"""
        if not self.alert_channels["slack"]["enabled"]:
            return
        
        # Implementation would use Slack webhook API
        # This is a placeholder for Slack integration
        pass
    
    def trigger_alert(self, alert_type: str, details: Dict[str, Any]):
        """Trigger security alert based on type"""
        subject = f"{alert_type} detected"
        message = f"""
Security Alert: {alert_type}
Time: {datetime.utcnow().isoformat()}
Details: {details}
"""
        
        # Send to all enabled channels
        self.send_email_alert(subject, message)
        self.send_webhook_alert({"type": alert_type, "details": details})
        self.send_slack_alert(message)


# Singleton instance
security_alert_manager = SecurityAlertManager()
