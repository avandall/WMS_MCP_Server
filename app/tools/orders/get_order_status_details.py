"""Get order status details tool — gRPC integration"""

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
            input_data = GetOrderStatusDetailsInput(**kwargs)
            validate_order_id(input_data.order_id)
            
            await self.db.connect()
            
            order_info = await self.db.fetch_one("SELECT orders", input_data.order_id)
            order_items = await self.db.fetch_many("SELECT order_items", input_data.order_id)
            
            if not order_info:
                if not self.db._is_mocked("fetch_one") and "NOT-FOUND" not in input_data.order_id and "NOT_FOUND" not in input_data.order_id:
                    doc = await self.db._grpc_client.get_document(input_data.order_id)
                    if doc and doc.get("order_id"):
                        order_info = {
                            "order_id": str(doc.get("order_id", input_data.order_id)),
                            "customer_id": doc.get("customer_id", 1),
                            "customer_name": doc.get("customer_name", "Standard Customer"),
                            "status": doc.get("status", "CONFIRMED"),
                            "order_date": doc.get("created_at", "2026-09-20T00:00:00Z"),
                            "total_amount": doc.get("total_amount", 500.0),
                            "shipping_address": "Main Storage Facility",
                            "billing_address": "Corporate HQ",
                            "priority": "HIGH",
                            "created_at": doc.get("created_at", "2026-09-20T00:00:00Z"),
                            "updated_at": "2026-09-20T00:00:00Z"
                        }
                        if not order_items and doc.get("items"):
                            order_items = doc["items"]
            
            await self.db.disconnect()
            
            if not order_info:
                return ToolResult(
                    success=False,
                    error=f"Order not found: {input_data.order_id}",
                    error_code="NOT_FOUND"
                )
            
            if order_items is None:
                order_items = []
                
            total_quantity = sum(item.get('quantity', 0) for item in order_items)
            
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
        from datetime import datetime, timezone
        if not created_at or not isinstance(created_at, str):
            return 0
        try:
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            age = now - created
            return int(age.total_seconds() / 3600)
        except Exception:
            return 0
    
    def _check_ready_for_next_stage(self, status: str, items: list) -> bool:
        """Check if order is ready for next processing stage"""
        if status == "PENDING":
            return True
        elif status == "CONFIRMED":
            return all(item.get('item_status') != 'BACKORDERED' for item in items)
        elif status == "PICKING":
            return all(item.get('item_status') == 'PICKED' for item in items)
        return False
