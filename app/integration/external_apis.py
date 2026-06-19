"""External API clients for shipping, payment, 3PL, and supplier integration"""

import httpx
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


class ShippingCarrierClient:
    """Base class for shipping carrier API clients"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def create_shipping_label(self, shipment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create shipping label"""
        response = await self.client.post(
            f"{self.base_url}/labels",
            json=shipment_data,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
    
    async def track_shipment(self, tracking_number: str) -> Dict[str, Any]:
        """Track shipment"""
        response = await self.client.get(
            f"{self.base_url}/track/{tracking_number}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class DHLClient(ShippingCarrierClient):
    """DHL shipping carrier client"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.dhl.com")


class FedExClient(ShippingCarrierClient):
    """FedEx shipping carrier client"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.fedex.com")


class UPSCClient(ShippingCarrierClient):
    """UPS shipping carrier client"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.ups.com")


class PaymentGatewayClient:
    """Payment gateway integration client"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def process_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment"""
        response = await self.client.post(
            f"{self.base_url}/payments",
            json=payment_data,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
    
    async def refund_payment(self, payment_id: str, amount: float) -> Dict[str, Any]:
        """Refund payment"""
        response = await self.client.post(
            f"{self.base_url}/refunds",
            json={"payment_id": payment_id, "amount": amount},
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class StripeClient(PaymentGatewayClient):
    """Stripe payment gateway client"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.stripe.com")


class PayPalClient(PaymentGatewayClient):
    """PayPal payment gateway client"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.paypal.com")


class ThreePLClient:
    """3PL (Third-Party Logistics) integration client"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create order in 3PL system"""
        response = await self.client.post(
            f"{self.base_url}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
    
    async def get_inventory(self, warehouse_id: str) -> Dict[str, Any]:
        """Get inventory from 3PL"""
        response = await self.client.get(
            f"{self.base_url}/inventory/{warehouse_id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class SupplierAPIClient:
    """Supplier API integration client"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place order with supplier"""
        response = await self.client.post(
            f"{self.base_url}/orders",
            json=order_data,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
    
    async def get_product_catalog(self) -> List[Dict[str, Any]]:
        """Get product catalog from supplier"""
        response = await self.client.get(
            f"{self.base_url}/products",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class WebhookHandler:
    """Webhook handler for receiving and processing webhooks"""
    
    def __init__(self):
        self.webhooks: Dict[str, callable] = {}
    
    def register_webhook(self, event_type: str, handler: callable):
        """Register webhook handler"""
        self.webhooks[event_type] = handler
    
    async def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook"""
        if event_type not in self.webhooks:
            return {"error": "No handler registered for this event type"}
        
        handler = self.webhooks[event_type]
        return await handler(payload)
    
    def verify_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)


# Singleton instances
webhook_handler = WebhookHandler()
