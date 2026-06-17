# WMS MCP Server Tool Guide

## Quick Start

Basic tool usage via MCP client:
```python
from mcp import ClientSession, StdioServerParameters

async with ClientSession(server_params) as session:
    result = await session.call_tool("check_stock_availability", {"sku_code": "SKU-001"})
```

## Common Workflows

### 1. Stock Check Workflow
1. check_stock_availability - Verify stock levels
2. get_low_stock_report - Check for low stock alerts

### 2. Order Processing Workflow  
1. get_order_status_details - Get order info
2. generate_picking_route - Optimize picking
3. suggest_packing_box - Get packing suggestions
4. create_shipping_label - Generate shipping label

### 3. Inventory Adjustment Workflow
1. update_inventory_quantity - Adjust stock
2. get_stock_movement_history - Verify changes
3. create_system_alert - Alert if needed

## Best Practices

- Always validate input parameters
- Use distributed locks for concurrent operations
- Check stock availability before updates
- Monitor queue status for backlogs
- Set appropriate timeouts for operations

## Troubleshooting

**Lock acquisition failed**: Check Redis status, retry with backoff
**Database errors**: Verify connection, check query performance
**Queue backlog**: Scale consumers, check processing rate
