"""Stress testing configuration for WMS MCP Server"""

try:
    from locust import HttpUser, task, constant
except ImportError:
    HttpUser = object
    task = lambda f: f
    constant = lambda s: s

import json


class StressTestUser(HttpUser):
    """Stress test user - high load, no wait time"""
    
    wait_time = constant(0.1)  # Minimal wait time for stress testing
    
    @task
    def rapid_tool_calls(self):
        """Rapid tool calls to stress test the system"""
        if hasattr(self, 'client'):
            self.client.post(
                "/tools/check_stock_availability",
                json={
                    "sku_code": "SKU-1060-6GB",
                    "warehouse_id": 1
                }
            )
