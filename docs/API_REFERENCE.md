# WMS MCP Server API Reference

## Overview

The WMS MCP Server provides 19 tools organized into 4 core layers and 5 advanced subsystems for warehouse management operations. All tools follow the MCP (Model Context Protocol) specification and can be called via stdio or SSE transport.

## Authentication & Authorization

### API Key Authentication
All tool calls require authentication via API key. Include the API key in the MCP client initialization:

```python
from mcp import ClientSession, StdioServerParameters

server_params = StdioServerParameters(
    command="python",
    args=["-m", "app.server"],
    env={"WMS_API_KEY": "your-api-key-here"}
)
```

### Authorization
Tools support role-based access control (RBAC). Users must have appropriate permissions to access specific tools:
- **Read operations**: `inventory:read`, `orders:read`, `monitoring:read`
- **Write operations**: `inventory:write`, `orders:write`, `transactions:write`
- **Admin operations**: `system:admin`, `users:admin`

## Error Codes

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| VALIDATION_ERROR | Invalid input parameters | 400 |
| NOT_FOUND | Resource not found | 404 |
| DATABASE_ERROR | Database operation failed | 500 |
| REDIS_ERROR | Redis operation failed | 500 |
| LOCK_ACQUISITION_FAILED | Could not acquire distributed lock | 409 |
| INSUFFICIENT_STOCK | Not enough inventory for operation | 400 |
| INSUFFICIENT_CAPACITY | No storage space available | 400 |
| QUEUE_ERROR | Message queue operation failed | 500 |
| UNAUTHORIZED | Missing or invalid authentication | 401 |
| FORBIDDEN | Insufficient permissions | 403 |
| RATE_LIMIT_EXCEEDED | Too many requests | 429 |

### Error Response Format
```json
{
  "success": false,
  "error": "Error message description",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "Additional error details"
  }
}
```

---

## Layer 1: Inventory & Slotting Tools

### check_stock_availability

Get physical and available stock quantities for a SKU at a specific warehouse.

**Endpoint**: `check_stock_availability`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sku_code | string | Yes | SKU code (e.g., SKU-1060-6GB) |
| warehouse_id | integer | No | Warehouse ID (defaults to primary warehouse) |

**Request Example**:
```json
{
  "sku_code": "SKU-1060-6GB",
  "warehouse_id": 1
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "sku_code": "SKU-1060-6GB",
    "warehouse_id": 1,
    "physical_quantity": 150,
    "available_quantity": 120,
    "reserved_quantity": 30,
    "in_transit_quantity": 0,
    "locations": [
      {
        "location_code": "ZONE-A-ROW-02-SHELF-01",
        "quantity": 100
      },
      {
        "location_code": "ZONE-A-ROW-03-SHELF-02",
        "quantity": 50
      }
    ]
  }
}
```

**Response Example (Error)**:
```json
{
  "success": false,
  "error": "No stock information found for SKU: SKU-1060-6GB",
  "error_code": "NOT_FOUND"
}
```

---

### inspect_shelf_capacity

Check the capacity and available space of a specific shelf/location based on physical volume.

**Endpoint**: `inspect_shelf_capacity`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| location_code | string | Yes | Location code (e.g., ZONE-A-ROW-02-SHELF-01) |

**Request Example**:
```json
{
  "location_code": "ZONE-A-ROW-02-SHELF-01"
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "location_code": "ZONE-A-ROW-02-SHELF-01",
    "total_capacity_cm3": 500000,
    "used_capacity_cm3": 350000,
    "available_capacity_cm3": 150000,
    "utilization_percent": 70,
    "item_count": 25,
    "max_weight_kg": 500,
    "current_weight_kg": 320,
    "zone": "ZONE-A",
    "shelf_type": "STANDARD"
  }
}
```

---

### abc_analysis_report

Get ABC classification for a SKU based on turnover frequency and value.

**Endpoint**: `abc_analysis_report`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sku_code | string | Yes | SKU code |

**Request Example**:
```json
{
  "sku_code": "SKU-1060-6GB"
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "sku_code": "SKU-1060-6GB",
    "abc_class": "A",
    "class_description": "High turnover, high value items",
    "turnover_rate": 15.5,
    "annual_demand": 1200,
    "unit_value": 299.99,
    "total_annual_value": 359988,
    "recommendation": "Store near shipping area for fast access",
    "reorder_frequency": "WEEKLY"
  }
}
```

**ABC Class Definitions**:
- **Class A**: High turnover (top 20% of items by value) - Store near shipping
- **Class B**: Medium turnover (next 30% of items by value) - Store in middle zones
- **Class C**: Low turnover (bottom 50% of items by value) - Store in back areas

---

### smart_slotting_optimizer

Suggest optimal storage location for a SKU based on its ABC classification.

**Endpoint**: `smart_slotting_optimizer`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sku_code | string | Yes | SKU code |
| quantity | integer | Yes | Quantity of items to be stored |

**Request Example**:
```json
{
  "sku_code": "SKU-1060-6GB",
  "quantity": 50
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "sku_code": "SKU-1060-6GB",
    "quantity": 50,
    "abc_class": "A",
    "recommended_locations": [
      {
        "location_code": "ZONE-A-ROW-01-SHELF-01",
        "reason": "Near shipping area for Class A items",
        "distance_to_shipping_m": 15,
        "available_capacity_cm3": 200000,
        "suitability_score": 95
      },
      {
        "location_code": "ZONE-A-ROW-02-SHELF-03",
        "reason": "Adjacent to primary recommendation",
        "distance_to_shipping_m": 20,
        "available_capacity_cm3": 180000,
        "suitability_score": 88
      }
    ],
    "optimization_criteria": ["abc_class", "distance_to_shipping", "available_capacity"]
  }
}
```

---

## Layer 2: Transactions & Movements Tools

### update_inventory_quantity

Increase or decrease inventory quantity at a specific location (used for inbound/outbound operations).

**Endpoint**: `update_inventory_quantity`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sku_code | string | Yes | SKU code |
| location_code | string | Yes | Location code |
| action | string | Yes | Action: INCREASE or DECREASE |
| quantity | integer | Yes | Quantity to increase/decrease (must be positive) |

**Request Example**:
```json
{
  "sku_code": "SKU-1060-6GB",
  "location_code": "ZONE-A-ROW-02-SHELF-01",
  "action": "INCREASE",
  "quantity": 25
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "sku_code": "SKU-1060-6GB",
    "location_code": "ZONE-A-ROW-02-SHELF-01",
    "action": "INCREASE",
    "quantity": 25,
    "message": "Successfully increased inventory by 25",
    "new_quantity": 125,
    "transaction_id": "TXN-2024-001234"
  }
}
```

**Response Example (Lock Error)**:
```json
{
  "success": false,
  "error": "Could not acquire lock - another operation is in progress",
  "error_code": "LOCK_ACQUISITION_FAILED"
}
```

**Notes**:
- Uses distributed locks to prevent race conditions
- Automatically invalidates cache after update
- Requires `inventory:write` permission

---

### move_stock_between_locations

Move stock quantity from one location to another (internal transfer).

**Endpoint**: `move_stock_between_locations`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sku_code | string | Yes | SKU code |
| from_location | string | Yes | Source location code |
| to_location | string | Yes | Destination location code |
| quantity | integer | Yes | Quantity to move |

**Request Example**:
```json
{
  "sku_code": "SKU-1060-6GB",
  "from_location": "ZONE-A-ROW-02-SHELF-01",
  "to_location": "ZONE-B-ROW-05-SHELF-03",
  "quantity": 30
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "sku_code": "SKU-1060-6GB",
    "from_location": "ZONE-A-ROW-02-SHELF-01",
    "to_location": "ZONE-B-ROW-05-SHELF-03",
    "quantity": 30,
    "message": "Successfully moved 30 units",
    "transfer_id": "TRF-2024-000567",
    "from_quantity_after": 70,
    "to_quantity_after": 30
  }
}
```

**Response Example (Insufficient Stock)**:
```json
{
  "success": false,
  "error": "Insufficient stock at source location",
  "error_code": "INSUFFICIENT_STOCK",
  "details": {
    "available_quantity": 25,
    "requested_quantity": 30
  }
}
```

---

### adjust_inventory_for_reason

Adjust inventory for discrepancies found during audits (stock adjustment).

**Endpoint**: `adjust_inventory_for_reason`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sku_code | string | Yes | SKU code |
| location_code | string | Yes | Location code |
| reason | string | Yes | Reason for adjustment (DAMAGED, LOST, FOUND, COUNT_ERROR) |
| quantity | integer | Yes | Quantity adjustment (positive for increase, negative for decrease) |

**Request Example**:
```json
{
  "sku_code": "SKU-1060-6GB",
  "location_code": "ZONE-A-ROW-02-SHELF-01",
  "reason": "DAMAGED",
  "quantity": -5
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "sku_code": "SKU-1060-6GB",
    "location_code": "ZONE-A-ROW-02-SHELF-01",
    "reason": "DAMAGED",
    "quantity": -5,
    "message": "Successfully adjusted inventory by -5",
    "adjustment_id": "ADJ-2024-000123",
    "previous_quantity": 100,
    "new_quantity": 95,
    "audit_trail": {
      "adjusted_by": "system",
      "adjusted_at": "2024-06-18T10:30:00Z",
      "reference": "AUDIT-2024-06-18"
    }
  }
}
```

**Valid Reasons**:
- `DAMAGED`: Items damaged during handling
- `LOST`: Items missing/unaccounted for
- `FOUND`: Items found during audit
- `COUNT_ERROR`: Correction of counting errors

---

## Layer 3: Concurrency & Monitoring Tools

### check_redis_locks

Check distributed locks on Redis for a specific resource to debug hanging APIs.

**Endpoint**: `check_redis_locks`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| resource_key | string | Yes | Resource key to check (e.g., lock:sku:SKU-1060-6GB or lock:order:123) |

**Request Example**:
```json
{
  "resource_key": "lock:sku:SKU-1060-6GB"
}
```

**Response Example (Success - Lock Found)**:
```json
{
  "success": true,
  "data": {
    "resource_key": "lock:sku:SKU-1060-6GB",
    "lock_exists": true,
    "lock_holder": "server-001",
    "lock_acquired_at": "2024-06-18T10:25:30Z",
    "lock_ttl_seconds": 25,
    "lock_age_seconds": 5,
    "status": "ACTIVE"
  }
}
```

**Response Example (No Lock)**:
```json
{
  "success": true,
  "data": {
    "resource_key": "lock:sku:SKU-1060-6GB",
    "lock_exists": false,
    "status": "NO_LOCK"
  }
}
```

---

### get_stock_movement_history

Get complete audit trail of stock movements for a SKU within a time range.

**Endpoint**: `get_stock_movement_history`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sku_code | string | Yes | SKU code |
| limit_days | integer | No | Number of days to look back (default: 7) |

**Request Example**:
```json
{
  "sku_code": "SKU-1060-6GB",
  "limit_days": 7
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "sku_code": "SKU-1060-6GB",
    "period_days": 7,
    "total_movements": 15,
    "movements": [
      {
        "transaction_id": "TXN-2024-001234",
        "timestamp": "2024-06-18T09:30:00Z",
        "type": "INBOUND",
        "quantity": 50,
        "location": "ZONE-A-ROW-02-SHELF-01",
        "reference": "PO-2024-00567"
      },
      {
        "transaction_id": "TXN-2024-001233",
        "timestamp": "2024-06-17T14:20:00Z",
        "type": "OUTBOUND",
        "quantity": -25,
        "location": "ZONE-A-ROW-02-SHELF-01",
        "reference": "ORDER-2024-00890"
      }
    ],
    "summary": {
      "total_inbound": 150,
      "total_outbound": 100,
      "net_change": 50
    }
  }
}
```

---

### view_message_queue_status

Check message queue backlog for order processing queues.

**Endpoint**: `view_message_queue_status`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| queue_name | string | Yes | Queue name (e.g., wms.order.process) |

**Request Example**:
```json
{
  "queue_name": "wms.order.process"
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "queue_name": "wms.order.process",
    "message_count": 1250,
    "consumer_count": 5,
    "messages_per_consumer": 250,
    "status": "BACKLOG",
    "oldest_message_age_seconds": 180,
    "processing_rate_per_minute": 50,
    "estimated_clearance_time_minutes": 25
  }
}
```

**Status Values**:
- `HEALTHY`: Processing normally
- `BACKLOG`: Messages accumulating
- `CRITICAL`: Severe backlog requiring attention

---

## Layer 4: Alerts & Reports Tools

### get_low_stock_report

Get list of items with available quantity at or below safety stock level.

**Endpoint**: `get_low_stock_report`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| threshold_qty | integer | No | Custom threshold quantity (optional) |

**Request Example**:
```json
{
  "threshold_qty": 10
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "report_generated_at": "2024-06-18T10:00:00Z",
    "threshold_quantity": 10,
    "total_items_below_threshold": 8,
    "items": [
      {
        "sku_code": "SKU-1060-6GB",
        "available_quantity": 5,
        "safety_stock": 20,
        "reorder_point": 15,
        "status": "CRITICAL",
        "recommended_action": "URGENT_REORDER"
      },
      {
        "sku_code": "SKU-RTX-3080",
        "available_quantity": 8,
        "safety_stock": 15,
        "reorder_point": 12,
        "status": "LOW",
        "recommended_action": "REORDER"
      }
    ]
  }
}
```

---

### create_system_alert

Create a system alert for monitoring or notification purposes.

**Endpoint**: `create_system_alert`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| alert_type | string | Yes | Alert type (CRITICAL, WARNING, INFO) |
| message | string | Yes | Alert message content |

**Request Example**:
```json
{
  "alert_type": "CRITICAL",
  "message": "Warehouse capacity at 95% - immediate attention required"
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "alert_id": "ALERT-2024-000456",
    "alert_type": "CRITICAL",
    "message": "Warehouse capacity at 95% - immediate attention required",
    "created_at": "2024-06-18T10:35:00Z",
    "status": "ACTIVE",
    "acknowledged": false,
    "notification_sent": true
  }
}
```

**Alert Types**:
- `CRITICAL`: Requires immediate attention
- `WARNING`: Attention needed but not urgent
- `INFO`: Informational notification

---

## Advanced Subsystem Tools

### get_order_status_details

Get detailed order status including items, customer info, and processing stage.

**Endpoint**: `get_order_status_details`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| order_id | string | Yes | Order ID |

**Request Example**:
```json
{
  "order_id": "ORDER-2024-00890"
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "order_info": {
      "order_id": "ORDER-2024-00890",
      "customer_id": "CUST-001234",
      "customer_name": "John Doe",
      "status": "PICKING",
      "status_description": "Items being picked from warehouse",
      "order_date": "2024-06-17T14:20:00Z",
      "total_amount": 599.98,
      "shipping_address": "123 Main St, City, State 12345",
      "priority": "STANDARD"
    },
    "order_items": [
      {
        "item_id": "ITEM-001",
        "sku_code": "SKU-1060-6GB",
        "quantity": 2,
        "unit_price": 299.99,
        "total_price": 599.98,
        "item_status": "PICKED"
      }
    ],
    "total_items": 1,
    "total_quantity": 2,
    "summary": {
      "order_id": "ORDER-2024-00890",
      "status": "PICKING",
      "customer": "John Doe",
      "total_amount": 599.98,
      "item_count": 1,
      "total_quantity": 2,
      "order_age_hours": 20,
      "ready_for_next_stage": true
    }
  }
}
```

**Order Status Values**:
- `PENDING`: Order received, awaiting processing
- `CONFIRMED`: Order confirmed, awaiting picking
- `PICKING`: Items being picked from warehouse
- `PICKED`: All items picked, awaiting packing
- `PACKING`: Order being packed
- `PACKED`: Order packed, awaiting shipping
- `SHIPPED`: Order shipped, in transit
- `DELIVERED`: Order delivered to customer
- `CANCELLED`: Order cancelled

---

### suggest_packing_box

Suggest optimal packing box size based on order items volume and weight.

**Endpoint**: `suggest_packing_box`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| order_id | string | Yes | Order ID |

**Request Example**:
```json
{
  "order_id": "ORDER-2024-00890"
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "order_id": "ORDER-2024-00890",
    "total_volume_cm3": 15000,
    "total_weight_kg": 2.5,
    "recommended_box": {
      "box_id": "BOX-MEDIUM-001",
      "box_name": "Medium Shipping Box",
      "dimensions_cm": {
        "length": 30,
        "width": 20,
        "height": 25
      },
      "volume_cm3": 15000,
      "max_weight_kg": 10,
      "utilization_percent": 85,
      "cost": 2.50
    },
    "alternative_boxes": [
      {
        "box_id": "BOX-LARGE-001",
        "box_name": "Large Shipping Box",
        "utilization_percent": 60,
        "cost": 3.00,
        "reason": "More space, higher cost"
      }
    ],
    "packing_instructions": [
      "Place heavier items at bottom",
      "Use bubble wrap for fragile items",
      "Fill void spaces with packing paper"
    ]
  }
}
```

---

### generate_picking_route

Generate optimized picking route for order items using TSP algorithm.

**Endpoint**: `generate_picking_route`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| order_id | string | Yes | Order ID |

**Request Example**:
```json
{
  "order_id": "ORDER-2024-00890"
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "order_id": "ORDER-2024-00890",
    "total_distance_m": 145,
    "estimated_time_minutes": 12,
    "route": [
      {
        "sequence": 1,
        "location_code": "ZONE-A-ROW-02-SHELF-01",
        "sku_code": "SKU-1060-6GB",
        "quantity": 2,
        "distance_from_previous_m": 0,
        "cumulative_distance_m": 0
      },
      {
        "sequence": 2,
        "location_code": "ZONE-B-ROW-05-SHELF-03",
        "sku_code": "SKU-RTX-3080",
        "quantity": 1,
        "distance_from_previous_m": 75,
        "cumulative_distance_m": 75
      },
      {
        "sequence": 3,
        "location_code": "ZONE-A-ROW-01-SHELF-05",
        "sku_code": "SKU-SSD-1TB",
        "quantity": 1,
        "distance_from_previous_m": 70,
        "cumulative_distance_m": 145
      }
    ],
    "optimization_method": "TSP_NEAREST_NEIGHBOR",
    "start_location": "PACKING_STATION",
    "end_location": "PACKING_STATION"
  }
}
```

---

### verify_incoming_po

Verify incoming purchase order against expected quantities.

**Endpoint**: `verify_incoming_po`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| po_number | string | Yes | Purchase order number |

**Request Example**:
```json
{
  "po_number": "PO-2024-00567"
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "po_number": "PO-2024-00567",
    "supplier_id": "SUPP-001",
    "supplier_name": "Tech Components Inc",
    "verification_status": "MATCHED",
    "expected_items": [
      {
        "sku_code": "SKU-1060-6GB",
        "expected_quantity": 50,
        "received_quantity": 50,
        "status": "MATCHED"
      },
      {
        "sku_code": "SKU-RTX-3080",
        "expected_quantity": 25,
        "received_quantity": 24,
        "status": "SHORTAGE"
      }
    ],
    "summary": {
      "total_items": 2,
      "matched_items": 1,
      "shortage_items": 1,
      "excess_items": 0,
      "discrepancy_found": true
    },
    "recommendation": "Process matched items, create shortage claim for SKU-RTX-3080"
  }
}
```

---

### assign_picking_task

Assign picking task to a specific user/worker.

**Endpoint**: `assign_picking_task`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| task_id | string | Yes | Task ID |
| user_id | string | Yes | User/worker ID |

**Request Example**:
```json
{
  "task_id": "TASK-2024-001234",
  "user_id": "USER-0056"
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "task_id": "TASK-2024-001234",
    "user_id": "USER-0056",
    "user_name": "Jane Smith",
    "assigned_at": "2024-06-18T10:40:00Z",
    "status": "ASSIGNED",
    "priority": "HIGH",
    "estimated_duration_minutes": 15,
    "deadline": "2024-06-18T11:00:00Z"
  }
}
```

---

### audit_user_permissions

Audit user permissions for specific actions.

**Endpoint**: `audit_user_permissions`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | string | Yes | User ID |
| action_required | string | Yes | Action to check (e.g., DELETE_STOCK, MODIFY_ORDERS) |

**Request Example**:
```json
{
  "user_id": "USER-0056",
  "action_required": "DELETE_STOCK"
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "user_id": "USER-0056",
    "user_name": "Jane Smith",
    "action_required": "DELETE_STOCK",
    "has_permission": true,
    "permission_source": "ROLE_WAREHOUSE_MANAGER",
    "granted_at": "2024-01-15T00:00:00Z",
    "expires_at": null,
    "restrictions": [],
    "audit_log": {
      "last_used": "2024-06-17T15:30:00Z",
      "usage_count": 45
    }
  }
}
```

---

### create_shipping_label

Generate shipping label via 3PL carrier integration.

**Endpoint**: `create_shipping_label`

**Method**: MCP Tool Call

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| order_id | string | Yes | Order ID |
| carrier_id | string | Yes | Carrier ID (e.g., DHL, FedEx, UPS) |

**Request Example**:
```json
{
  "order_id": "ORDER-2024-00890",
  "carrier_id": "DHL"
}
```

**Response Example (Success)**:
```json
{
  "success": true,
  "data": {
    "order_id": "ORDER-2024-00890",
    "carrier_id": "DHL",
    "tracking_number": "DHL-1234567890",
    "label_url": "https://labels.dhl.com/LABEL-123456.pdf",
    "shipping_cost": 15.99,
    "estimated_delivery_date": "2024-06-20",
    "service_level": "EXPRESS",
    "label_generated_at": "2024-06-18T10:45:00Z",
    "package_details": {
      "weight_kg": 2.5,
      "dimensions_cm": {
        "length": 30,
        "width": 20,
        "height": 25
      }
    }
  }
}
```

**Supported Carriers**:
- `DHL`: DHL Express
- `FedEx`: FedEx Express
- `UPS`: UPS Ground/Express
- `GHTK`: Giao Hang Tiet Kiem (Vietnam)
- `GHN`: Giao Hang Nhanh (Vietnam)

---

## Rate Limiting

All tools are subject to rate limiting to prevent abuse:

| Tool Category | Rate Limit | Burst Limit |
|---------------|-------------|-------------|
| Read operations | 100 requests/minute | 200 requests/minute |
| Write operations | 50 requests/minute | 100 requests/minute |
| Admin operations | 20 requests/minute | 50 requests/minute |

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Request limit per window
- `X-RateLimit-Remaining`: Remaining requests in window
- `X-RateLimit-Reset`: Unix timestamp when window resets

---

## Versioning

Current API version: `v1.0`

Version format: `MAJOR.MINOR.PATCH`
- MAJOR: Breaking changes
- MINOR: New features, backward compatible
- PATCH: Bug fixes, backward compatible

---

## Support

For API support:
- Documentation: `/docs`
- Issues: GitHub Issues
- Email: support@wms-mcp.example.com
