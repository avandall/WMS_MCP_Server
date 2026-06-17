# WMS MCP Server API Reference

## Error Codes
VALIDATION_ERROR, NOT_FOUND, DATABASE_ERROR, REDIS_ERROR, LOCK_ACQUISITION_FAILED, INSUFFICIENT_STOCK, INSUFFICIENT_CAPACITY, QUEUE_ERROR

## Inventory Tools
- check_stock_availability: Get stock quantities
- inspect_shelf_capacity: Check shelf capacity
- abc_analysis_report: ABC classification
- smart_slotting_optimizer: Suggest storage location

## Transaction Tools  
- update_inventory_quantity: Adjust inventory
- move_stock_between_locations: Move stock
- adjust_inventory_for_reason: Audit adjustments

## Monitoring Tools
- check_redis_locks: Inspect locks
- get_stock_movement_history: Movement audit
- view_message_queue_status: Queue status

## Alert Tools
- get_low_stock_report: Low stock alerts
- create_system_alert: System alerts

## Order Tools
- get_order_status_details: Order details
- suggest_packing_box: Packing suggestions

## Other Tools
- generate_picking_route: Optimize picking
- verify_incoming_po: PO verification
- assign_picking_task: Task assignment
- audit_user_permissions: Permission audit
- create_shipping_label: Shipping labels
