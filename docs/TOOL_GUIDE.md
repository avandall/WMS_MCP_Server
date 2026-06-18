# WMS MCP Server Tool Guide

## Overview

This guide provides comprehensive usage instructions for all 19 WMS MCP Server tools, organized by layer and subsystem. Each tool includes practical examples, use cases, and integration patterns.

## Quick Start

### Basic Tool Usage

```python
from mcp import ClientSession, StdioServerParameters

server_params = StdioServerParameters(
    command="python",
    args=["-m", "app.server"],
    env={"WMS_API_KEY": "your-api-key-here"}
)

async with ClientSession(server_params) as session:
    await session.initialize()
    
    # Call a tool
    result = await session.call_tool("check_stock_availability", {
        "sku_code": "SKU-1060-6GB",
        "warehouse_id": 1
    })
    
    if result.success:
        print(f"Available stock: {result.data['available_quantity']}")
    else:
        print(f"Error: {result.error}")
```

### Error Handling Pattern

```python
async def safe_tool_call(session, tool_name, params):
    """Safe tool call with error handling"""
    result = await session.call_tool(tool_name, params)
    
    if not result.success:
        # Handle specific error codes
        if result.error_code == "LOCK_ACQUISITION_FAILED":
            # Retry with backoff
            return await retry_with_backoff(tool_name, params)
        elif result.error_code == "VALIDATION_ERROR":
            # Fix input and retry
            return await fix_and_retry(tool_name, params)
        else:
            # Log and handle other errors
            logger.error(f"Tool {tool_name} failed: {result.error}")
            return None
    
    return result.data
```

---

## Layer 1: Inventory & Slotting Tools

### check_stock_availability

**Purpose**: Get physical and available stock quantities for a SKU

**When to Use**:
- Before processing orders to ensure stock availability
- During inventory audits to verify stock levels
- For real-time stock display in applications

**Example Usage**:
```python
# Check stock before order processing
async def process_order(session, order):
    for item in order.items:
        result = await session.call_tool("check_stock_availability", {
            "sku_code": item.sku_code,
            "warehouse_id": order.warehouse_id
        })
        
        if result.success:
            available = result.data['available_quantity']
            if available < item.quantity:
                return f"Insufficient stock for {item.sku_code}: {available} available, {item.quantity} requested"
        else:
            return f"Error checking stock: {result.error}"
    
    return "All items in stock"
```

**Best Practices**:
- Always check stock availability before write operations
- Use warehouse_id parameter for multi-warehouse environments
- Cache results for frequently accessed SKUs
- Monitor reserved quantities separately

---

### inspect_shelf_capacity

**Purpose**: Check capacity and available space of a specific shelf/location

**When to Use**:
- Before placing new inventory in a location
- During warehouse space planning
- For capacity utilization monitoring

**Example Usage**:
```python
# Find suitable location for incoming inventory
async def find_suitable_location(session, sku_code, quantity):
    # Get ABC classification
    abc_result = await session.call_tool("abc_analysis_report", {
        "sku_code": sku_code
    })
    
    abc_class = abc_result.data['abc_class']
    
    # Check candidate locations based on ABC class
    if abc_class == 'A':
        locations = ["ZONE-A-ROW-01-SHELF-01", "ZONE-A-ROW-02-SHELF-01"]
    else:
        locations = ["ZONE-B-ROW-05-SHELF-03", "ZONE-C-ROW-10-SHELF-05"]
    
    for location in locations:
        capacity_result = await session.call_tool("inspect_shelf_capacity", {
            "location_code": location
        })
        
        if capacity_result.success:
            available = capacity_result.data['available_capacity_cm3']
            if available >= quantity * 1000:  # Assume 1000 cm3 per unit
                return location
    
    return None  # No suitable location found
```

**Best Practices**:
- Check capacity before stock placement
- Monitor utilization percentages regularly
- Consider weight limits alongside volume
- Plan for future growth when assessing capacity

---

### abc_analysis_report

**Purpose**: Get ABC classification for a SKU based on turnover and value

**When to Use**:
- During slotting optimization
- For inventory prioritization
- When planning storage locations

**Example Usage**:
```python
# Prioritize inventory management based on ABC class
async def prioritize_inventory(session):
    skus = ["SKU-1060-6GB", "SKU-RTX-3080", "SKU-SSD-1TB"]
    
    class_a_items = []
    class_b_items = []
    class_c_items = []
    
    for sku in skus:
        result = await session.call_tool("abc_analysis_report", {
            "sku_code": sku
        })
        
        if result.success:
            abc_class = result.data['abc_class']
            if abc_class == 'A':
                class_a_items.append(sku)
            elif abc_class == 'B':
                class_b_items.append(sku)
            else:
                class_c_items.append(sku)
    
    return {
        "high_priority": class_a_items,
        "medium_priority": class_b_items,
        "low_priority": class_c_items
    }
```

**Best Practices**:
- Review ABC classifications quarterly
- Use ABC data for slotting decisions
- Monitor turnover rate changes
- Update classifications based on seasonal trends

---

### smart_slotting_optimizer

**Purpose**: Suggest optimal storage location based on ABC classification

**When to Use**:
- During inbound receiving
- When reorganizing warehouse layout
- For new SKU placement

**Example Usage**:
```python
# Optimize placement for incoming inventory
async def place_incoming_inventory(session, incoming_items):
    placement_plan = []
    
    for item in incoming_items:
        result = await session.call_tool("smart_slotting_optimizer", {
            "sku_code": item.sku_code,
            "quantity": item.quantity
        })
        
        if result.success:
            recommended = result.data['recommended_locations'][0]
            placement_plan.append({
                "sku_code": item.sku_code,
                "quantity": item.quantity,
                "location": recommended['location_code'],
                "suitability_score": recommended['suitability_score']
            })
    
    return placement_plan
```

**Best Practices**:
- Follow recommendations for Class A items
- Consider manual overrides for special cases
- Monitor placement effectiveness
- Update recommendations based on actual picking patterns

---

## Layer 2: Transactions & Movements Tools

### update_inventory_quantity

**Purpose**: Increase or decrease inventory at a specific location

**When to Use**:
- During inbound receiving
- For outbound order fulfillment
- For inventory adjustments

**Example Usage**:
```python
# Process inbound receiving
async def process_inbound(session, receipt):
    for item in receipt.items:
        # Check capacity first
        capacity_result = await session.call_tool("inspect_shelf_capacity", {
            "location_code": item.location_code
        })
        
        if capacity_result.success and capacity_result.data['available_capacity_cm3'] >= item.volume:
            # Update inventory
            result = await session.call_tool("update_inventory_quantity", {
                "sku_code": item.sku_code,
                "location_code": item.location_code,
                "action": "INCREASE",
                "quantity": item.quantity
            })
            
            if not result.success:
                logger.error(f"Failed to update inventory: {result.error}")
        else:
            logger.warning(f"Insufficient capacity at {item.location_code}")
```

**Best Practices**:
- Always check capacity before increasing inventory
- Use distributed locks for concurrent operations
- Verify stock availability before decreasing
- Log all quantity changes for audit trail

---

### move_stock_between_locations

**Purpose**: Move stock quantity between locations

**When to Use**:
- During inventory reorganization
- For zone transfers
- When consolidating stock

**Example Usage**:
```python
# Consolidate stock to reduce locations
async def consolidate_stock(session, sku_code):
    # Get all locations with this SKU
    stock_result = await session.call_tool("check_stock_availability", {
        "sku_code": sku_code
    })
    
    locations = stock_result.data['locations']
    
    if len(locations) > 1:
        # Consolidate to first location
        target_location = locations[0]['location_code']
        
        for location in locations[1:]:
            result = await session.call_tool("move_stock_between_locations", {
                "sku_code": sku_code,
                "from_location": location['location_code'],
                "to_location": target_location,
                "quantity": location['quantity']
            })
            
            if result.success:
                logger.info(f"Moved {location['quantity']} units to {target_location}")
```

**Best Practices**:
- Verify source stock before moving
- Check destination capacity
- Use for internal transfers only
- Track movement for audit purposes

---

### adjust_inventory_for_reason

**Purpose**: Adjust inventory for discrepancies (damaged, lost, found)

**When to Use**:
- During inventory audits
- When damaged goods are discovered
- For found items during cycle counts

**Example Usage**:
```python
# Process audit discrepancies
async def process_audit_discrepancies(session, audit_results):
    for discrepancy in audit_results:
        if discrepancy.type == "DAMAGED":
            result = await session.call_tool("adjust_inventory_for_reason", {
                "sku_code": discrepancy.sku_code,
                "location_code": discrepancy.location_code,
                "reason": "DAMAGED",
                "quantity": -discrepancy.quantity
            })
        elif discrepancy.type == "FOUND":
            result = await session.call_tool("adjust_inventory_for_reason", {
                "sku_code": discrepancy.sku_code,
                "location_code": discrepancy.location_code,
                "reason": "FOUND",
                "quantity": discrepancy.quantity
            })
        
        if result.success:
            logger.info(f"Adjusted inventory: {result.data['message']}")
```

**Best Practices**:
- Always document the reason for adjustment
- Use appropriate reason codes
- Get approval for significant adjustments
- Monitor adjustment frequency for patterns

---

## Layer 3: Concurrency & Monitoring Tools

### check_redis_locks

**Purpose**: Check distributed locks for debugging hanging operations

**When to Use**:
- When operations appear stuck
- For debugging race conditions
- During performance troubleshooting

**Example Usage**:
```python
# Debug stuck operation
async def debug_stuck_operation(session, sku_code):
    lock_key = f"lock:inventory:{sku_code}:*"
    
    result = await session.call_tool("check_redis_locks", {
        "resource_key": lock_key
    })
    
    if result.success and result.data['lock_exists']:
        lock_info = result.data
        logger.warning(f"Lock held by {lock_info['lock_holder']} for {lock_info['lock_age_seconds']}s")
        
        if lock_info['lock_age_seconds'] > 300:  # 5 minutes
            logger.error("Lock appears stale - may need manual intervention")
    else:
        logger.info("No lock found - operation may have completed")
```

**Best Practices**:
- Check locks before manual intervention
- Monitor lock age for stale locks
- Use appropriate lock timeouts
- Document lock investigation results

---

### get_stock_movement_history

**Purpose**: Get audit trail of stock movements

**When to Use**:
- During inventory investigations
- For audit compliance
- When tracking discrepancies

**Example Usage**:
```python
# Investigate stock discrepancy
async def investigate_discrepancy(session, sku_code, expected_qty, actual_qty):
    if expected_qty != actual_qty:
        # Get movement history
        result = await session.call_tool("get_stock_movement_history", {
            "sku_code": sku_code,
            "limit_days": 30
        })
        
        if result.success:
            movements = result.data['movements']
            net_change = result.data['summary']['net_change']
            
            logger.info(f"Net change in 30 days: {net_change}")
            logger.info(f"Total movements: {len(movements)}")
            
            # Analyze for anomalies
            for movement in movements:
                if movement['quantity'] > 100:  # Large movement threshold
                    logger.warning(f"Large movement detected: {movement}")
```

**Best Practices**:
- Use appropriate time ranges for investigations
- Analyze patterns in movement history
- Cross-reference with other records
- Document investigation findings

---

### view_message_queue_status

**Purpose**: Check message queue backlog for order processing

**When to Use**:
- When orders are processing slowly
- For system health monitoring
- Before scaling consumers

**Example Usage**:
```python
# Monitor queue health
async def monitor_queue_health(session):
    queues = ["wms.order.process", "wms.inventory.update", "wms.shipping.label"]
    
    for queue in queues:
        result = await session.call_tool("view_message_queue_status", {
            "queue_name": queue
        })
        
        if result.success:
            status = result.data['status']
            message_count = result.data['message_count']
            
            if status == "CRITICAL":
                await session.call_tool("create_system_alert", {
                    "alert_type": "CRITICAL",
                    "message": f"Queue {queue} critical: {message_count} messages backlog"
                })
            elif status == "BACKLOG":
                logger.warning(f"Queue {queue} backlog: {message_count} messages")
```

**Best Practices**:
- Monitor queue status regularly
- Set up alerts for critical backlogs
- Scale consumers based on backlog
- Investigate processing rate drops

---

## Layer 4: Alerts & Reports Tools

### get_low_stock_report

**Purpose**: Get list of items at or below safety stock level

**When to Use**:
- For reorder planning
- During inventory reviews
- For proactive stock management

**Example Usage**:
```python
# Generate reorder recommendations
async def generate_reorder_recommendations(session):
    result = await session.call_tool("get_low_stock_report", {
        "threshold_qty": 10
    })
    
    if result.success:
        items = result.data['items']
        
        for item in items:
            if item['status'] == 'CRITICAL':
                # Urgent reorder
                await create_purchase_order(item['sku_code'], item['safety_stock'] * 2)
            elif item['status'] == 'LOW':
                # Standard reorder
                await create_purchase_order(item['sku_code'], item['reorder_point'])
        
        return f"Generated {len(items)} reorder recommendations"
```

**Best Practices**:
- Run low stock reports daily
- Set appropriate safety stock levels
- Prioritize critical items
- Monitor reorder lead times

---

### create_system_alert

**Purpose**: Create system alerts for monitoring and notification

**When to Use**:
- When detecting critical issues
- For proactive monitoring
- During error conditions

**Example Usage**:
```python
# Monitor warehouse capacity
async def monitor_warehouse_capacity(session):
    result = await session.call_tool("inspect_shelf_capacity", {
        "location_code": "ZONE-A-ROW-01-SHELF-01"
    })
    
    if result.success:
        utilization = result.data['utilization_percent']
        
        if utilization > 95:
            await session.call_tool("create_system_alert", {
                "alert_type": "CRITICAL",
                "message": f"Warehouse capacity critical: {utilization}% utilized"
            })
        elif utilization > 85:
            await session.call_tool("create_system_alert", {
                "alert_type": "WARNING",
                "message": f"Warehouse capacity high: {utilization}% utilized"
            })
```

**Best Practices**:
- Use appropriate alert types
- Include actionable information in messages
- Set up alert escalation policies
- Monitor alert frequency for false positives

---

## Advanced Subsystem Tools

### get_order_status_details

**Purpose**: Get detailed order status and information

**When to Use**:
- For order tracking
- During customer service
- For order processing workflows

**Example Usage**:
```python
# Process order through fulfillment
async def process_order_fulfillment(session, order_id):
    # Get order details
    result = await session.call_tool("get_order_status_details", {
        "order_id": order_id
    })
    
    if result.success:
        order_info = result.data['order_info']
        status = order_info['status']
        
        if status == "CONFIRMED":
            # Generate picking route
            await generate_picking_route(session, order_id)
        elif status == "PICKED":
            # Suggest packing box
            await suggest_packing_box(session, order_id)
        elif status == "PACKED":
            # Create shipping label
            await create_shipping_label(session, order_id, "DHL")
```

**Best Practices**:
- Check order status before each step
- Monitor order age for SLA compliance
- Use status descriptions for user communication
- Track order processing time

---

### suggest_packing_box

**Purpose**: Suggest optimal packing box based on order items

**When to Use**:
- During order packing
- For shipping cost optimization
- When planning packaging inventory

**Example Usage**:
```python
# Optimize packing for order
async def pack_order(session, order_id):
    result = await session.call_tool("suggest_packing_box", {
        "order_id": order_id
    })
    
    if result.success:
        box = result.data['recommended_box']
        instructions = result.data['packing_instructions']
        
        logger.info(f"Using box: {box['box_name']} (utilization: {box['utilization_percent']}%)")
        
        for instruction in instructions:
            logger.info(f"Instruction: {instruction}")
        
        return box
```

**Best Practices**:
- Follow packing instructions
- Consider alternative boxes for cost optimization
- Monitor box utilization rates
- Update box catalog based on usage

---

### generate_picking_route

**Purpose**: Generate optimized picking route using TSP algorithm

**When to Use**:
- Before order picking
- For route optimization
- When planning picker assignments

**Example Usage**:
```python
# Assign picking task with optimized route
async def assign_picking_with_route(session, order_id, user_id):
    # Generate route
    route_result = await session.call_tool("generate_picking_route", {
        "order_id": order_id
    })
    
    if route_result.success:
        route = route_result.data['route']
        estimated_time = route_result.data['estimated_time_minutes']
        
        # Create task with route info
        task_id = f"TASK-{order_id}"
        
        assign_result = await session.call_tool("assign_picking_task", {
            "task_id": task_id,
            "user_id": user_id
        })
        
        if assign_result.success:
            logger.info(f"Assigned task {task_id} to {user_id}")
            logger.info(f"Estimated time: {estimated_time} minutes")
            logger.info(f"Route stops: {len(route)}")
```

**Best Practices**:
- Use generated routes for efficiency
- Monitor actual vs estimated times
- Consider picker experience in assignments
- Update location data for accuracy

---

### verify_incoming_po

**Purpose**: Verify incoming purchase order against expected quantities

**When to Use**:
- During inbound receiving
- For supplier quality control
- When processing purchase orders

**Example Usage**:
```python
# Process incoming shipment
async def process_incoming_shipment(session, po_number, received_items):
    result = await session.call_tool("verify_incoming_po", {
        "po_number": po_number
    })
    
    if result.success:
        verification = result.data
        
        if verification['verification_status'] == "MATCHED":
            # Process all items
            for item in verification['expected_items']:
                await update_inventory_quantity(session, item)
        else:
            # Handle discrepancies
            for item in verification['expected_items']:
                if item['status'] == "SHORTAGE":
                    await create_shortage_claim(item)
                elif item['status'] == "EXCESS":
                    await process_excess_item(item)
```

**Best Practices**:
- Verify all incoming shipments
- Document discrepancies with suppliers
- Process matched items immediately
- Create claims for shortages promptly

---

### assign_picking_task

**Purpose**: Assign picking task to a specific user/worker

**When to Use**:
- During order processing
- For workload distribution
- When managing picker assignments

**Example Usage**:
```python
# Distribute picking workload
async def distribute_picking_workload(session, orders, available_workers):
    tasks = []
    
    for i, order in enumerate(orders):
        worker = available_workers[i % len(available_workers)]
        task_id = f"TASK-{order['order_id']}"
        
        result = await session.call_tool("assign_picking_task", {
            "task_id": task_id,
            "user_id": worker['user_id']
        })
        
        if result.success:
            tasks.append({
                "task_id": task_id,
                "worker": worker['name'],
                "deadline": result.data['deadline']
            })
    
    return tasks
```

**Best Practices**:
- Balance workload across workers
- Consider worker skills and experience
- Monitor task completion rates
- Adjust assignments based on performance

---

### audit_user_permissions

**Purpose**: Audit user permissions for specific actions

**When to Use**:
- Before sensitive operations
- For security audits
- When troubleshooting access issues

**Example Usage**:
```python
# Check permissions before sensitive operation
async def perform_sensitive_operation(session, user_id, action):
    result = await session.call_tool("audit_user_permissions", {
        "user_id": user_id,
        "action_required": action
    })
    
    if result.success and result.data['has_permission']:
        # Perform operation
        logger.info(f"User {user_id} has permission for {action}")
        return await execute_operation(action)
    else:
        logger.warning(f"User {user_id} lacks permission for {action}")
        return None
```

**Best Practices**:
- Always audit before sensitive operations
- Log permission checks for audit trail
- Review permissions regularly
- Implement principle of least privilege

---

### create_shipping_label

**Purpose**: Generate shipping label via 3PL carrier integration

**When to Use**:
- During order shipping
- For label generation
- When integrating with carriers

**Example Usage**:
```python
# Process order shipping
async def ship_order(session, order_id, carrier_id):
    result = await session.call_tool("create_shipping_label", {
        "order_id": order_id,
        "carrier_id": carrier_id
    })
    
    if result.success:
        label_info = result.data
        tracking_number = label_info['tracking_number']
        label_url = label_info['label_url']
        
        logger.info(f"Generated label: {tracking_number}")
        logger.info(f"Label URL: {label_url}")
        
        # Download and print label
        await download_and_print_label(label_url)
        
        return tracking_number
```

**Best Practices**:
- Verify carrier availability before generating labels
- Test label generation in staging
- Monitor carrier API performance
- Handle carrier-specific requirements

---

## Step-by-Step Tutorials

### Tutorial 1: Complete Order Fulfillment Workflow

This tutorial demonstrates the complete order fulfillment process from order confirmation to shipping.

```python
async def complete_order_fulfillment(session, order_id):
    """Complete order fulfillment workflow"""
    
    # Step 1: Get order details
    print("Step 1: Getting order details...")
    order_result = await session.call_tool("get_order_status_details", {
        "order_id": order_id
    })
    
    if not order_result.success:
        return f"Failed to get order details: {order_result.error}"
    
    order_info = order_result.data['order_info']
    print(f"Order status: {order_info['status']}")
    
    # Step 2: Generate picking route
    print("\nStep 2: Generating picking route...")
    route_result = await session.call_tool("generate_picking_route", {
        "order_id": order_id
    })
    
    if not route_result.success:
        return f"Failed to generate route: {route_result.error}"
    
    route = route_result.data['route']
    print(f"Generated route with {len(route)} stops")
    print(f"Estimated time: {route_result.data['estimated_time_minutes']} minutes")
    
    # Step 3: Assign picking task
    print("\nStep 3: Assigning picking task...")
    task_id = f"TASK-{order_id}"
    assign_result = await session.call_tool("assign_picking_task", {
        "task_id": task_id,
        "user_id": "USER-0056"
    })
    
    if not assign_result.success:
        return f"Failed to assign task: {assign_result.error}"
    
    print(f"Task {task_id} assigned to USER-0056")
    
    # Step 4: Suggest packing box
    print("\nStep 4: Suggesting packing box...")
    box_result = await session.call_tool("suggest_packing_box", {
        "order_id": order_id
    })
    
    if not box_result.success:
        return f"Failed to suggest box: {box_result.error}"
    
    box = box_result.data['recommended_box']
    print(f"Recommended box: {box['box_name']}")
    print(f"Utilization: {box['utilization_percent']}%")
    
    # Step 5: Create shipping label
    print("\nStep 5: Creating shipping label...")
    label_result = await session.call_tool("create_shipping_label", {
        "order_id": order_id,
        "carrier_id": "DHL"
    })
    
    if not label_result.success:
        return f"Failed to create label: {label_result.error}"
    
    tracking_number = label_result.data['tracking_number']
    print(f"Shipping label created: {tracking_number}")
    
    return "Order fulfillment completed successfully"
```

### Tutorial 2: Inbound Receiving Process

This tutorial shows how to process incoming inventory from a purchase order.

```python
async def process_inbound_receiving(session, po_number, received_items):
    """Process inbound receiving workflow"""
    
    # Step 1: Verify purchase order
    print("Step 1: Verifying purchase order...")
    verify_result = await session.call_tool("verify_incoming_po", {
        "po_number": po_number
    })
    
    if not verify_result.success:
        return f"PO verification failed: {verify_result.error}"
    
    verification = verify_result.data
    print(f"Verification status: {verification['verification_status']}")
    
    # Step 2: Process each item
    print("\nStep 2: Processing received items...")
    for item in received_items:
        # Get ABC classification for slotting
        abc_result = await session.call_tool("abc_analysis_report", {
            "sku_code": item['sku_code']
        })
        
        # Get optimal location
        slot_result = await session.call_tool("smart_slotting_optimizer", {
            "sku_code": item['sku_code'],
            "quantity": item['quantity']
        })
        
        if slot_result.success:
            location = slot_result.data['recommended_locations'][0]['location_code']
            print(f"Placing {item['sku_code']} at {location}")
            
            # Update inventory
            update_result = await session.call_tool("update_inventory_quantity", {
                "sku_code": item['sku_code'],
                "location_code": location,
                "action": "INCREASE",
                "quantity": item['quantity']
            })
            
            if update_result.success:
                print(f"Updated inventory: +{item['quantity']} units")
            else:
                print(f"Failed to update inventory: {update_result.error}")
    
    # Step 3: Check for discrepancies
    print("\nStep 3: Checking for discrepancies...")
    if verification['summary']['discrepancy_found']:
        print("Discrepancies found - creating alerts")
        await session.call_tool("create_system_alert", {
            "alert_type": "WARNING",
            "message": f"PO {po_number} has discrepancies"
        })
    
    return "Inbound receiving completed"
```

### Tutorial 3: Inventory Audit Process

This tutorial demonstrates how to perform an inventory audit and handle discrepancies.

```python
async def perform_inventory_audit(session, audit_items):
    """Perform inventory audit workflow"""
    
    discrepancies = []
    
    # Step 1: Check each audited item
    print("Step 1: Checking audited items...")
    for item in audit_items:
        # Get current system stock
        stock_result = await session.call_tool("check_stock_availability", {
            "sku_code": item['sku_code'],
            "warehouse_id": item['warehouse_id']
        })
        
        if stock_result.success:
            system_qty = stock_result.data['physical_quantity']
            audit_qty = item['counted_quantity']
            
            if system_qty != audit_qty:
                discrepancy = {
                    'sku_code': item['sku_code'],
                    'location_code': item['location_code'],
                    'system_qty': system_qty,
                    'audit_qty': audit_qty,
                    'difference': audit_qty - system_qty
                }
                discrepancies.append(discrepanpancy)
                print(f"Discrepancy found for {item['sku_code']}: {discrepancy['difference']}")
    
    # Step 2: Process discrepancies
    print("\nStep 2: Processing discrepancies...")
    for discrepancy in discrepancies:
        if discrepancy['difference'] > 0:
            # Found extra items
            result = await session.call_tool("adjust_inventory_for_reason", {
                "sku_code": discrepancy['sku_code'],
                "location_code": discrepancy['location_code'],
                "reason": "FOUND",
                "quantity": discrepancy['difference']
            })
        else:
            # Missing items
            result = await session.call_tool("adjust_inventory_for_reason", {
                "sku_code": discrepancy['sku_code'],
                "location_code": discrepancy['location_code'],
                "reason": "LOST",
                "quantity": discrepancy['difference']
            })
        
        if result.success:
            print(f"Adjusted {discrepancy['sku_code']}: {result.data['message']}")
    
    # Step 3: Get movement history for investigation
    print("\nStep 3: Investigating movement history...")
    for discrepancy in discrepancies:
        history_result = await session.call_tool("get_stock_movement_history", {
            "sku_code": discrepancy['sku_code'],
            "limit_days": 30
        })
        
        if history_result.success:
            movements = history_result.data['movements']
            print(f"{discrepancy['sku_code']}: {len(movements)} movements in last 30 days")
    
    # Step 4: Create audit summary
    print("\nStep 4: Creating audit summary...")
    summary = {
        'total_items_audited': len(audit_items),
        'discrepancies_found': len(discrepancies),
        'total_adjustment': sum(d['difference'] for d in discrepancies)
    }
    
    print(f"Audit complete: {summary['discrepancies_found']} discrepancies found")
    
    return summary
```

---

## Tool Composition Patterns

### Pattern 1: Stock Check Before Operation

Always verify stock availability before write operations:

```python
async def safe_stock_update(session, sku_code, location_code, quantity, action):
    """Safe stock update with pre-check"""
    
    # Check current stock
    stock_result = await session.call_tool("check_stock_availability", {
        "sku_code": sku_code
    })
    
    if action == "DECREASE":
        available = stock_result.data['available_quantity']
        if available < quantity:
            return f"Insufficient stock: {available} available, {quantity} requested"
    
    # Perform update
    update_result = await session.call_tool("update_inventory_quantity", {
        "sku_code": sku_code,
        "location_code": location_code,
        "action": action,
        "quantity": quantity
    })
    
    return update_result
```

### Pattern 2: Capacity Check Before Placement

Verify location capacity before placing inventory:

```python
async def safe_stock_placement(session, sku_code, location_code, quantity):
    """Safe stock placement with capacity check"""
    
    # Check capacity
    capacity_result = await session.call_tool("inspect_shelf_capacity", {
        "location_code": location_code
    })
    
    if capacity_result.success:
        available = capacity_result.data['available_capacity_cm3']
        required = quantity * 1000  # Assume 1000 cm3 per unit
        
        if available < required:
            return f"Insufficient capacity: {available} available, {required} required"
    
    # Place inventory
    update_result = await session.call_tool("update_inventory_quantity", {
        "sku_code": sku_code,
        "location_code": location_code,
        "action": "INCREASE",
        "quantity": quantity
    })
    
    return update_result
```

### Pattern 3: Lock Retry with Backoff

Implement retry logic for lock acquisition failures:

```python
async def update_with_retry(session, params, max_retries=3):
    """Update inventory with lock retry"""
    
    for attempt in range(max_retries):
        result = await session.call_tool("update_inventory_quantity", params)
        
        if result.success:
            return result
        
        if result.error_code == "LOCK_ACQUISITION_FAILED":
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                return result
        
        # Non-retryable error
        return result
    
    return None
```

### Pattern 4: Audit Trail for Sensitive Operations

Always create audit trail for sensitive operations:

```python
async def audited_inventory_adjustment(session, params, user_id):
    """Inventory adjustment with audit trail"""
    
    # Perform adjustment
    result = await session.call_tool("adjust_inventory_for_reason", params)
    
    if result.success:
        # Log to audit trail
        logger.info(f"Inventory adjustment by {user_id}: {result.data}")
        
        # Check if permission was valid
        permission_result = await session.call_tool("audit_user_permissions", {
            "user_id": user_id,
            "action_required": "ADJUST_INVENTORY"
        })
        
        if not permission_result.data['has_permission']:
            logger.warning(f"User {user_id} performed adjustment without proper permission")
    
    return result
```

---

## Best Practices

### 1. Input Validation

Always validate inputs before calling tools:

```python
def validate_sku_code(sku_code):
    """Validate SKU code format"""
    if not sku_code or not isinstance(sku_code, str):
        raise ValueError("SKU code must be a non-empty string")
    if not sku_code.startswith("SKU-"):
        raise ValueError("SKU code must start with 'SKU-'")
    return sku_code

# Use before tool calls
sku_code = validate_sku_code(user_input)
result = await session.call_tool("check_stock_availability", {"sku_code": sku_code})
```

### 2. Distributed Locks

Use distributed locks for concurrent operations:

```python
# Tools that use locks automatically:
# - update_inventory_quantity
# - move_stock_between_locations

# Monitor locks if operations seem stuck
result = await session.call_tool("check_redis_locks", {
    "resource_key": f"lock:inventory:{sku_code}:{location_code}"
})
```

### 3. Stock Availability Checks

Always check stock availability before updates:

```python
# Before decreasing stock
stock_result = await session.call_tool("check_stock_availability", {
    "sku_code": sku_code
})

if stock_result.data['available_quantity'] >= requested_quantity:
    # Proceed with update
    await update_inventory_quantity(...)
```

### 4. Queue Monitoring

Monitor queue status for system health:

```python
# Check queue status periodically
result = await session.call_tool("view_message_queue_status", {
    "queue_name": "wms.order.process"
})

if result.data['status'] == "CRITICAL":
    # Alert and scale consumers
    await create_system_alert(...)
```

### 5. Timeout Management

Set appropriate timeouts for operations:

```python
import asyncio

async def call_with_timeout(session, tool_name, params, timeout=30):
    """Call tool with timeout"""
    try:
        result = await asyncio.wait_for(
            session.call_tool(tool_name, params),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"Tool {tool_name} timed out after {timeout}s")
        return None
```

---

## Anti-Patterns

### 1. Ignoring Error Codes

**Bad**: Generic error handling
```python
if not result.success:
    await retry_operation()  # Retries validation errors
```

**Good**: Specific error handling
```python
if result.error_code == "LOCK_ACQUISITION_FAILED":
    await retry_with_backoff()
elif result.error_code == "VALIDATION_ERROR":
    fix_input_and_retry()
```

### 2. Skipping Pre-checks

**Bad**: Direct update without checks
```python
await update_inventory_quantity(params)  # May fail due to insufficient stock
```

**Good**: Check before update
```python
stock = await check_stock_availability(...)
if stock['available_quantity'] >= quantity:
    await update_inventory_quantity(params)
```

### 3. Hardcoding Values

**Bad**: Hardcoded location codes
```python
location = "ZONE-A-ROW-01-SHELF-01"  # Not flexible
```

**Good**: Use optimization tools
```python
result = await smart_slotting_optimizer(...)
location = result.data['recommended_locations'][0]['location_code']
```

### 4. No Audit Trail

**Bad**: Silent adjustments
```python
await adjust_inventory_for_reason(params)  # No logging
```

**Good**: Audit all adjustments
```python
result = await adjust_inventory_for_reason(params)
logger.info(f"Adjustment made: {result.data['adjustment_id']}")
```

### 5. Ignoring Capacity Limits

**Bad**: Place without capacity check
```python
await update_inventory_quantity(params)  # May exceed capacity
```

**Good**: Check capacity first
```python
capacity = await inspect_shelf_capacity(...)
if capacity['available_capacity_cm3'] >= required:
    await update_inventory_quantity(params)
```

---

## Troubleshooting

### Issue: Lock Acquisition Failed

**Symptoms**: Operations fail with `LOCK_ACQUISITION_FAILED` error

**Diagnosis**:
```python
result = await session.call_tool("check_redis_locks", {
    "resource_key": f"lock:inventory:{sku_code}:{location_code}"
})
```

**Solutions**:
1. Wait and retry with exponential backoff
2. Check for stuck locks using `check_redis_locks`
3. Verify lock timeout settings
4. Reduce concurrent operations on same resource

### Issue: Database Connection Errors

**Symptoms**: Operations fail with `DATABASE_ERROR`

**Diagnosis**:
```python
# Check database connectivity
# Review database logs
# Monitor connection pool usage
```

**Solutions**:
1. Verify database is running
2. Check connection pool settings
3. Implement retry logic for transient errors
4. Monitor database performance metrics

### Issue: Queue Backlog

**Symptoms**: Orders processing slowly, queue status shows BACKLOG

**Diagnosis**:
```python
result = await session.call_tool("view_message_queue_status", {
    "queue_name": "wms.order.process"
})
```

**Solutions**:
1. Scale consumer instances
2. Check for slow processing operations
3. Optimize tool execution time
4. Implement batch processing

### Issue: Insufficient Stock Errors

**Symptoms**: Operations fail with `INSUFFICIENT_STOCK`

**Diagnosis**:
```python
result = await session.call_tool("check_stock_availability", {
    "sku_code": sku_code
})
```

**Solutions**:
1. Check stock availability before operations
2. Implement reservation system
3. Monitor low stock alerts
4. Plan for safety stock levels

### Issue: Capacity Exceeded

**Symptoms**: Operations fail with `INSUFFICIENT_CAPACITY`

**Diagnosis**:
```python
result = await session.call_tool("inspect_shelf_capacity", {
    "location_code": location_code
})
```

**Solutions**:
1. Check capacity before placement
2. Use `smart_slotting_optimizer` for placement
3. Monitor utilization rates
4. Plan for capacity expansion

---

## Performance Optimization

### 1. Caching Strategy

Cache frequently accessed data:

```python
# Cache stock availability for 5 minutes
cache = {}

async def get_cached_stock(session, sku_code):
    if sku_code in cache and time.time() - cache[sku_code]['time'] < 300:
        return cache[sku_code]['data']
    
    result = await session.call_tool("check_stock_availability", {
        "sku_code": sku_code
    })
    
    if result.success:
        cache[sku_code] = {
            'data': result.data,
            'time': time.time()
        }
    
    return result.data
```

### 2. Batch Operations

Batch multiple operations when possible:

```python
# Process multiple items in batch
async def batch_update_inventory(session, items):
    results = []
    
    for item in items:
        result = await session.call_tool("update_inventory_quantity", {
            "sku_code": item['sku_code'],
            "location_code": item['location_code'],
            "action": item['action'],
            "quantity": item['quantity']
        })
        results.append(result)
    
    return results
```

### 3. Parallel Processing

Process independent operations in parallel:

```python
import asyncio

async def parallel_stock_check(session, sku_codes):
    """Check multiple SKUs in parallel"""
    tasks = [
        session.call_tool("check_stock_availability", {"sku_code": sku})
        for sku in sku_codes
    ]
    
    results = await asyncio.gather(*tasks)
    return results
```

---

## Support

For tool usage support:
- Review API_REFERENCE.md for detailed tool documentation
- Check ERROR_HANDLING.md for error resolution
- Monitor system health via Grafana dashboards
- Contact support for persistent issues
