"""Create shipping label tool"""

from typing import Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_order_id
from app.utils.error_handlers import handle_tool_error
from datetime import datetime
import uuid
import json


class CreateShippingLabelInput(BaseModel):
    """Input schema for create_shipping_label"""
    order_id: str = Field(..., description="Order ID")
    carrier_id: str = Field(..., description="Carrier ID (e.g., GHTK, GHN, DHL)")


class CreateShippingLabel(BaseTool):
    """Create shipping label by calling carrier API"""
    
    name = "create_shipping_label"
    description = "Generate shipping label by calling external carrier API to get tracking number"
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Order ID"
                },
                "carrier_id": {
                    "type": "string",
                    "description": "Carrier ID (e.g., GHTK, GHN, DHL)"
                }
            },
            "required": ["order_id", "carrier_id"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = CreateShippingLabelInput(**kwargs)
            
            # Validate input
            validate_order_id(input_data.order_id)
            
            # Connect to database
            await self.db.connect()
            
            # Get order details
            order_query = """
                SELECT 
                    order_id,
                    customer_id,
                    customer_name,
                    customer_phone,
                    shipping_address,
                    shipping_city,
                    shipping_postal_code,
                    total_weight_kg,
                    total_volume_cm3,
                    status
                FROM orders
                WHERE order_id = $1
            """
            
            order_info = await self.db.fetch_one(order_query, input_data.order_id)
            
            if not order_info:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"Order not found: {input_data.order_id}",
                    error_code="NOT_FOUND"
                )
            
            # Check if order is ready for shipping
            if order_info.get('status') not in ['PACKED', 'READY_TO_SHIP']:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"Order is not ready for shipping. Current status: {order_info.get('status')}",
                    error_code="INVALID_STATUS"
                )
            
            # Get carrier information
            carrier_query = """
                SELECT 
                    carrier_id,
                    carrier_name,
                    api_endpoint,
                    requires_auth
                FROM shipping_carriers
                WHERE carrier_id = $1
            """
            
            carrier_info = await self.db.fetch_one(carrier_query, input_data.carrier_id)
            
            if not carrier_info:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"Carrier not found: {input_data.carrier_id}",
                    error_code="NOT_FOUND"
                )
            
            # Simulate carrier API call (in production, this would be a real API call)
            shipping_result = await self._call_carrier_api(
                carrier_info, 
                order_info, 
                input_data.order_id
            )
            
            if not shipping_result['success']:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"Carrier API call failed: {shipping_result['error']}",
                    error_code="CARRIER_API_ERROR"
                )
            
            # Save shipping label information
            label_id = f"LBL-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
            
            save_query = """
                INSERT INTO shipping_labels (
                    label_id, order_id, carrier_id, tracking_number, 
                    label_data, created_at
                ) VALUES ($1, $2, $3, $4, $5, NOW())
            """
            
            await self.db.execute(
                save_query,
                label_id,
                input_data.order_id,
                input_data.carrier_id,
                shipping_result['tracking_number'],
                json.dumps(shipping_result['label_data'])
            )
            
            # Update order status
            update_query = """
                UPDATE orders
                SET status = 'SHIPPED',
                    shipping_carrier = $1,
                    tracking_number = $2,
                    shipped_at = NOW()
                WHERE order_id = $3
            """
            
            await self.db.execute(update_query, input_data.carrier_id, shipping_result['tracking_number'], input_data.order_id)
            
            # Close connection
            await self.db.disconnect()
            
            return ToolResult(
                success=True,
                data={
                    "label_id": label_id,
                    "order_id": input_data.order_id,
                    "carrier_id": input_data.carrier_id,
                    "carrier_name": carrier_info.get('carrier_name'),
                    "tracking_number": shipping_result['tracking_number'],
                    "label_data": shipping_result['label_data'],
                    "label_url": shipping_result.get('label_url'),
                    "created_at": datetime.utcnow().isoformat(),
                    "message": f"Shipping label created successfully. Tracking number: {shipping_result['tracking_number']}"
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
    
    async def _call_carrier_api(
        self, 
        carrier_info: Dict[str, Any], 
        order_info: Dict[str, Any],
        order_id: str
    ) -> Dict[str, Any]:
        """Simulate carrier API call (in production, this would call real carrier API)"""
        # This is a simulation - in production, you would make actual HTTP requests
        # to the carrier's API using their authentication and format requirements
        
        carrier_id = carrier_info['carrier_id']
        
        # Generate mock tracking number based on carrier
        tracking_number = self._generate_mock_tracking_number(carrier_id, order_id)
        
        # Generate mock label data
        label_data = {
            "carrier": carrier_info['carrier_name'],
            "tracking_number": tracking_number,
            "ship_to": {
                "name": order_info.get('customer_name'),
                "phone": order_info.get('customer_phone'),
                "address": order_info.get('shipping_address'),
                "city": order_info.get('shipping_city'),
                "postal_code": order_info.get('shipping_postal_code')
            },
            "package": {
                "weight_kg": order_info.get('total_weight_kg', 0),
                "dimensions": {
                    "volume_cm3": order_info.get('total_volume_cm3', 0)
                }
            },
            "service": "STANDARD",
            "label_format": "PDF"
        }
        
        return {
            "success": True,
            "tracking_number": tracking_number,
            "label_data": label_data,
            "label_url": f"https://api.{carrier_id.lower()}.com/labels/{tracking_number}"
        }
    
    def _generate_mock_tracking_number(self, carrier_id: str, order_id: str) -> str:
        """Generate mock tracking number for testing"""
        carrier_prefixes = {
            "GHTK": "GHTK",
            "GHN": "GHN",
            "DHL": "DHL",
            "FedEx": "FEDEX",
            "UPS": "UPS"
        }
        
        prefix = carrier_prefixes.get(carrier_id, "TRK")
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        unique = uuid.uuid4().hex[:8].upper()
        
        return f"{prefix}{timestamp}{unique}"
