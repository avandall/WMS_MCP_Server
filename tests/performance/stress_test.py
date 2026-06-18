"""Stress testing configuration for WMS MCP Server"""

from locust import HttpUser, task, constant
import json


class StressTestUser(HttpUser):
    """Stress test user - high load, no wait time"""
    
    wait_time = constant(0.1)  # Minimal wait time for stress testing
    
    @task
    def rapid_tool_calls(self):
        """Rapid tool calls to stress test the system"""
        self.client.post(
            "/tools/check_stock_availability",
            json={
                "sku_code": "SKU-1060-6GB",
                "warehouse_id": 1
            }
        )
