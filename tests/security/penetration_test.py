"""Penetration testing script for WMS MCP Server"""

import requests
import json
from typing import Dict, Any


class PenetrationTester:
    """Penetration testing for WMS MCP Server"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        print("Testing SQL injection...")
        
        # Test various SQL injection payloads
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE inventory; --",
            "' UNION SELECT * FROM users --"
        ]
        
        for payload in payloads:
            response = requests.post(
                f"{self.base_url}/tools/check_stock_availability",
                json={"sku_code": payload, "warehouse_id": 1}
            )
            
            if response.status_code == 200:
                print(f"WARNING: Potential SQL injection vulnerability with payload: {payload}")
    
    def test_authentication_bypass(self):
        """Test for authentication bypass"""
        print("Testing authentication bypass...")
        
        # Test without API key
        response = requests.post(
            f"{self.base_url}/tools/check_stock_availability",
            json={"sku_code": "SKU-1060-6GB", "warehouse_id": 1}
        )
        
        if response.status_code == 200:
            print("WARNING: API accessible without authentication")
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        print("Testing rate limiting...")
        
        # Send many requests rapidly
        for i in range(100):
            response = requests.post(
                f"{self.base_url}/tools/check_stock_availability",
                json={"sku_code": "SKU-1060-6GB", "warehouse_id": 1}
            )
            
            if response.status_code == 429:
                print(f"Rate limiting activated after {i+1} requests")
                break
        else:
            print("WARNING: No rate limiting detected")
    
    def test_xss(self):
        """Test for XSS vulnerabilities"""
        print("Testing XSS vulnerabilities...")
        
        payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')"
        ]
        
        for payload in payloads:
            response = requests.post(
                f"{self.base_url}/tools/check_stock_availability",
                json={"sku_code": payload, "warehouse_id": 1}
            )
            
            if payload in response.text:
                print(f"WARNING: Potential XSS vulnerability with payload: {payload}")
    
    def run_all_tests(self):
        """Run all penetration tests"""
        print("Starting penetration testing...")
        print("=" * 50)
        
        self.test_sql_injection()
        self.test_authentication_bypass()
        self.test_rate_limiting()
        self.test_xss()
        
        print("=" * 50)
        print("Penetration testing completed")


if __name__ == "__main__":
    tester = PenetrationTester()
    tester.run_all_tests()
