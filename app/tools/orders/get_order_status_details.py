"""Get order status details tool"""

from typing import Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_order_id
from app.utils.error_handlers import handle_tool_error


class GetOrderStatusDetailsInput(BaseModel):
    """Input schema for get_order_status_details"""
    order_id: str = Field(..., description="Order ID")


class GetOrderStatusDetails(BaseTool):
    """Get detailed order status and information"""
    
    name = "get_order_status_details"
    description = "Get detailed order status including items, customer info, and current processing stage"
    
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
                }
            },
            "required": ["order_id"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = GetOrderStatusDetailsInput(**kwargs)
            
            # Validate input
            validate_order_id(input_data.order_id)
            
            # Connect to database
            await self.db.connect()
            
            # Get order details
            query = """
                SELECT 
                    order_id,
                    customer_id,
                    customer_name,
                    status,
                    order_date,
                    total_amount,
                    shipping_address,
                    billing_address,
                    priority,
                    created_at,
                    updated_at
                FROM orders
                WHERE order_id = $1
            """
            
            order_info = await self.db.fetch_one(query, input_data.order_id)
            
            if not order_info:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"Order not found: {input_data.order_id}",
                    error_code="NOT_FOUND"
                )
            
            # Get order items
            items_query = """
                SELECT 
                    item_id,
                    sku_code,
                    quantity,
                    unit_price,
                    total_price,
                    item_status
                FROM order_items
                WHERE order_id = $1
                ORDER BY item_id
            """
            
            order_items = await self.db.fetch_many(items_query, input_data.order_id)
            
            # Calculate totals
            total_quantity = sum(item.get('quantity', 0) for item in order_items)
            
            # Close connection
            await self.db.disconnect()
            
            # Add status interpretation
            status_descriptions = {
                "PENDING": "Order received, awaiting processing",
                "CONFIRMED": "Order confirmed, awaiting picking",
                "PICKING": "Items being picked from warehouse",
                "PICKED": "All items picked, awaiting packing",
                "PACKING": "Order being packed",
                "PACKED": "Order packed, awaiting shipping",
                "SHIPPED": "Order shipped, in transit",
                "DELIVERED": "Order delivered to customer",
                "CANCELLED": "Order cancelled"
            }
            
            order_info['status_description'] = status_descriptions.get(
                order_info.get('status'), 'Unknown status'
            )
            
            return ToolResult(
                success=True,
                data={
                    "order_info": order_info,
                    "order_items": order_items,
                    "total_items": len(order_items),
                    "total_quantity": total_quantity,
                    "summary": self._generate_order_summary(order_info, order_items)
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
    
    def _generate_order_summary(self, order_info: Dict[str, Any], items: list) -> Dict[str, Any]:
        """Generate order summary"""
        return {
            "order_id": order_info.get('order_id'),
            "status": order_info.get('status'),
            "customer": order_info.get('customer_name'),
            "total_amount": order_info.get('total_amount'),
            "item_count": len(items),
            "total_quantity": sum(item.get('quantity', 0) for item in items),
            "order_age_hours": self._calculate_order_age(order_info.get('created_at')),
            "ready_for_next_stage": self._check_ready_for_next_stage(order_info.get('status'), items)
        }
    
    def _calculate_order_age(self, created_at: str) -> int:
        """Calculate order age in hours"""
        from datetime import datetime
        if not created_at:
            return 0
        try:
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.utcnow()
            age = now - created
            return int(age.total_seconds() / 3600)
        except:
            return 0
    
    def _check_ready_for_next_stage(self, status: str, items: list) -> bool:
        """Check if order is ready for next processing stage"""
        if status == "PENDING":
            return True  # Ready for confirmation
        elif status == "CONFIRMED":
            return all(item.get('item_status') != 'BACKORDERED' for item in items)
        elif status == "PICKING":
            return all(item.get('item_status') == 'PICKED' for item in items)
        return False
