"""Verify incoming PO tool"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_quantity
from app.utils.error_handlers import handle_tool_error


class VerifyIncomingPOInput(BaseModel):
    """Input schema for verify_incoming_po"""
    po_number: str = Field(..., description="Purchase Order number")
    received_items: list = Field(..., description="List of received items with SKU and quantity")


class VerifyIncomingPO(BaseTool):
    """Verify incoming purchase order against expected delivery"""
    
    name = "verify_incoming_po"
    description = "Compare received items against purchase order to identify shortages or overages"
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "po_number": {
                    "type": "string",
                    "description": "Purchase Order number"
                },
                "received_items": {
                    "type": "array",
                    "description": "List of received items with SKU and quantity",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sku_code": {"type": "string"},
                            "quantity": {"type": "integer"}
                        }
                    }
                }
            },
            "required": ["po_number", "received_items"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = VerifyIncomingPOInput(**kwargs)
            
            # Connect to database
            await self.db.connect()
            
            # Get PO details
            po_query = """
                SELECT 
                    po_number,
                    supplier_id,
                    supplier_name,
                    expected_date,
                    status
                FROM purchase_orders
                WHERE po_number = $1
            """
            
            po_info = await self.db.fetch_one(po_query, input_data.po_number)
            
            if not po_info:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"Purchase Order not found: {input_data.po_number}",
                    error_code="NOT_FOUND"
                )
            
            # Get PO items
            po_items_query = """
                SELECT 
                    sku_code,
                    ordered_quantity,
                    unit_price,
                    received_quantity
                FROM purchase_order_items
                WHERE po_number = $1
            """
            
            po_items = await self.db.fetch_many(po_items_query, input_data.po_number)
            
            # Close connection
            await self.db.disconnect()
            
            # Compare received vs expected
            verification_result = self._verify_receipt(input_data.received_items, po_items)
            
            return ToolResult(
                success=True,
                data={
                    "po_number": input_data.po_number,
                    "po_info": po_info,
                    "verification_result": verification_result,
                    "overall_status": verification_result['overall_status'],
                    "requires_action": verification_result['requires_action'],
                    "recommendations": self._generate_recommendations(verification_result)
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
    
    def _verify_receipt(self, received_items: list, po_items: list) -> Dict[str, Any]:
        """Verify received items against PO"""
        # Create maps for easy comparison
        received_map = {item['sku_code']: item['quantity'] for item in received_items}
        po_map = {item['sku_code']: item['ordered_quantity'] for item in po_items}
        
        discrepancies = []
        all_skus = set(received_map.keys()) | set(po_map.keys())
        
        total_ordered = sum(po_map.values())
        total_received = sum(received_map.get(sku, 0) for sku in po_map.keys())
        
        for sku in all_skus:
            ordered = po_map.get(sku, 0)
            received = received_map.get(sku, 0)
            
            if ordered != received:
                discrepancy_type = "SHORTAGE" if received < ordered else "OVERAGE"
                discrepancies.append({
                    "sku_code": sku,
                    "ordered": ordered,
                    "received": received,
                    "difference": received - ordered,
                    "type": discrepancy_type
                })
        
        # Determine overall status
        if not discrepancies:
            overall_status = "MATCH"
            requires_action = False
        elif any(d['type'] == 'SHORTAGE' for d in discrepancies):
            overall_status = "DISCREPANCY"
            requires_action = True
        else:
            overall_status = "OVERAGE"
            requires_action = True
        
        return {
            "overall_status": overall_status,
            "requires_action": requires_action,
            "total_ordered": total_ordered,
            "total_received": total_received,
            "discrepancies": discrepancies,
            "discrepancy_count": len(discrepancies)
        }
    
    def _generate_recommendations(self, verification_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on verification"""
        recommendations = []
        
        if verification_result['overall_status'] == "MATCH":
            recommendations.append("Receipt matches PO exactly - proceed with receiving")
        else:
            for discrepancy in verification_result['discrepancies']:
                if discrepancy['type'] == 'SHORTAGE':
                    recommendations.append(
                        f"Shortage for {discrepancy['sku_code']}: "
                        f"{discrepancy['difference']} units missing - contact supplier"
                    )
                else:
                    recommendations.append(
                        f"Overage for {discrepancy['sku_code']}: "
                        f"{discrepancy['difference']} extra units - update PO or return"
                    )
        
        return recommendations
