"""Locust load testing configuration for WMS MCP Server"""

from locust import HttpUser, task, between
import json


class WMSMCPUser(HttpUser):
    """Simulated user for load testing"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session"""
        # Login or setup if needed
        pass
    
    @task(3)
    def check_stock_availability(self):
        """Test check_stock_availability tool"""
        self.client.post(
            "/tools/check_stock_availability",
            json={
                "sku_code": "SKU-1060-6GB",
                "warehouse_id": 1
            }
        )
    
    @task(2)
    def get_order_status(self):
        """Test get_order_status_details tool"""
        self.client.post(
            "/tools/get_order_status_details",
            json={
                "order_id": "ORDER-2024-00890"
            }
        )
    
    @task(1)
    def update_inventory(self):
        """Test update_inventory_quantity tool"""
        self.client.post(
            "/tools/update_inventory_quantity",
            json={
                "sku_code": "SKU-1060-6GB",
                "location_code": "ZONE-A-ROW-01-SHELF-01",
                "action": "INCREASE",
                "quantity": 10
            }
        )
    
    @task(1)
    def check_redis_locks(self):
        """Test check_redis_locks tool"""
        self.client.post(
            "/tools/check_redis_locks",
            json={}
        )
