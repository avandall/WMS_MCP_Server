# 🔌 WMS MCP Server: Model Context Protocol Tool Provider

WMS MCP Server is a specialized tool-calling microservice built on top of the **Model Context Protocol (MCP)** specification. It exposes the core operational database, business routines, and algorithms of the warehouse management system to LLM agents.

---

## 🛠️ Tool Inventory (19 Production Tools)

Tools are organized into distinct layers and advanced subsystems inside the server:

### Layer 1: Inventory & Slotting
- `check_stock_availability` — Checks real-time stock levels and availability by SKU code.
- `inspect_shelf_capacity` — Measures capacity levels on shelves.
- `abc_analysis_report` — Classifies inventory items based on frequency and value.
- `smart_slotting_optimizer` — Suggests optimal warehouse locations for products.

### Layer 2: Transactions & Movements
- `update_inventory_quantity` — Modifies stock quantities directly.
- `move_stock_between_locations` — Handles internal stock transfers between locations.
- `adjust_inventory_for_reason` — Adjusts discrepant stock values with reasoning logging.

### Layer 3: Concurrency & Monitoring
- `check_redis_locks` — Inspects active distributed locks.
- `get_stock_movement_history` — Queries audit history logs for stock items.
- `view_message_queue_status` — Inspects queue backlog status and queue metrics.

### Layer 4: Alerts & Reports
- `get_low_stock_report` — Generates reports on items falling below safety stocks.
- `create_system_alert` — Creates and logs operational system alerts.

### Layer 5: Advanced Subsystems (Orders & Shipping)
- `get_order_status_details` — Retrieves processing statuses for customer orders.
- `suggest_packing_box` — Optimizes box size selections for shipping items.
- `generate_picking_route` — Suggests optimal routes for picking waves.
- `verify_incoming_po` — Audits incoming purchase orders.
- `assign_picking_task` — Automatically delegates tasks to warehouse operators.
- `audit_user_permissions` — Checks user permission matrices.
- `create_shipping_label` — Coordinates with 3PL APIs to generate shipping labels.

---

## 🚀 Execution & Integration

### Stdio Transport (Standard Agent Integration)
Most agents invoke the server in a subprocess using stdio. Configure your client session with the following command parameters:
- **Command**: `python`
- **Args**: `["-m", "main"]` (run from the repository root)

### Development Setup
Install standard packages and launch:
```bash
uv sync
python main.py
```

### Running Tests
Execute unit and integration tests covering tool validations:
```bash
pytest tests/
```
