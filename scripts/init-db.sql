-- Database initialization script for WMS MCP Server

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables (basic structure - expand as needed)

-- Products table
CREATE TABLE IF NOT EXISTS products (
    sku_code VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    length DECIMAL(10,2),
    width DECIMAL(10,2),
    height DECIMAL(10,2),
    weight DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory stock table
CREATE TABLE IF NOT EXISTS inventory_stock (
    id SERIAL PRIMARY KEY,
    sku_code VARCHAR(50) NOT NULL,
    warehouse_id INTEGER,
    location_code VARCHAR(50),
    physical_qty INTEGER DEFAULT 0,
    available_qty INTEGER DEFAULT 0,
    reserved_qty INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sku_code) REFERENCES products(sku_code)
);

-- Warehouse locations table
CREATE TABLE IF NOT EXISTS warehouse_locations (
    location_code VARCHAR(50) PRIMARY KEY,
    zone_id VARCHAR(20),
    row_id VARCHAR(20),
    shelf_id VARCHAR(20),
    max_volume DECIMAL(10,2),
    max_weight DECIMAL(10,2),
    current_volume DECIMAL(10,2) DEFAULT 0,
    current_weight DECIMAL(10,2) DEFAULT 0,
    x_coordinate DECIMAL(10,2),
    y_coordinate DECIMAL(10,2),
    z_coordinate DECIMAL(10,2)
);

-- Stock movements table (audit trail)
CREATE TABLE IF NOT EXISTS stock_movements (
    movement_id SERIAL PRIMARY KEY,
    sku_code VARCHAR(50) NOT NULL,
    from_location VARCHAR(50),
    to_location VARCHAR(50),
    quantity INTEGER NOT NULL,
    movement_type VARCHAR(20) NOT NULL,
    reason VARCHAR(50),
    reference_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50)
);

-- ABC analysis table
CREATE TABLE IF NOT EXISTS abc_analysis (
    sku_code VARCHAR(50) PRIMARY KEY,
    abc_class CHAR(1) NOT NULL,
    turnover_rate DECIMAL(10,2),
    annual_demand INTEGER,
    avg_order_value DECIMAL(10,2),
    last_calculated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sku_code) REFERENCES products(sku_code)
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50),
    customer_name VARCHAR(255),
    customer_phone VARCHAR(20),
    status VARCHAR(20) DEFAULT 'PENDING',
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10,2),
    shipping_address TEXT,
    shipping_city VARCHAR(100),
    shipping_postal_code VARCHAR(20),
    billing_address TEXT,
    priority VARCHAR(20) DEFAULT 'NORMAL',
    total_weight_kg DECIMAL(10,2),
    total_volume_cm3 DECIMAL(10,2),
    shipping_carrier VARCHAR(50),
    tracking_number VARCHAR(50),
    shipped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Order items table
CREATE TABLE IF NOT EXISTS order_items (
    item_id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    sku_code VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2),
    total_price DECIMAL(10,2),
    item_status VARCHAR(20) DEFAULT 'PENDING',
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (sku_code) REFERENCES products(sku_code)
);

-- Purchase orders table
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_number VARCHAR(50) PRIMARY KEY,
    supplier_id VARCHAR(50),
    supplier_name VARCHAR(255),
    expected_date DATE,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Purchase order items table
CREATE TABLE IF NOT EXISTS purchase_order_items (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(50) NOT NULL,
    sku_code VARCHAR(50) NOT NULL,
    ordered_quantity INTEGER NOT NULL,
    received_quantity INTEGER DEFAULT 0,
    unit_price DECIMAL(10,2),
    FOREIGN KEY (po_number) REFERENCES purchase_orders(po_number),
    FOREIGN KEY (sku_code) REFERENCES products(sku_code)
);

-- Packing boxes table
CREATE TABLE IF NOT EXISTS packing_boxes (
    box_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    length DECIMAL(10,2),
    width DECIMAL(10,2),
    height DECIMAL(10,2),
    max_weight DECIMAL(10,2),
    active BOOLEAN DEFAULT true
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255),
    role VARCHAR(50),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    current_task_id VARCHAR(50),
    warehouse_access INTEGER[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User permissions table
CREATE TABLE IF NOT EXISTS user_permissions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    permission VARCHAR(50) NOT NULL,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Role permissions table
CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL,
    permission VARCHAR(50) NOT NULL
);

-- Picking tasks table
CREATE TABLE IF NOT EXISTS picking_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    task_type VARCHAR(50),
    order_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'UNASSIGNED',
    assigned_user_id VARCHAR(50),
    priority VARCHAR(20) DEFAULT 'NORMAL',
    assigned_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (assigned_user_id) REFERENCES users(user_id)
);

-- Shipping carriers table
CREATE TABLE IF NOT EXISTS shipping_carriers (
    carrier_id VARCHAR(50) PRIMARY KEY,
    carrier_name VARCHAR(100),
    api_endpoint VARCHAR(255),
    requires_auth BOOLEAN DEFAULT false
);

-- Shipping labels table
CREATE TABLE IF NOT EXISTS shipping_labels (
    label_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50),
    carrier_id VARCHAR(50),
    tracking_number VARCHAR(100),
    label_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (carrier_id) REFERENCES shipping_carriers(carrier_id)
);

-- System alerts table
CREATE TABLE IF NOT EXISTS system_alerts (
    alert_id VARCHAR(50) PRIMARY KEY,
    alert_type VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    source VARCHAR(100),
    details JSONB,
    resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_inventory_stock_sku ON inventory_stock(sku_code);
CREATE INDEX IF NOT EXISTS idx_inventory_stock_location ON inventory_stock(location_code);
CREATE INDEX IF NOT EXISTS idx_stock_movements_sku ON stock_movements(sku_code);
CREATE INDEX IF NOT EXISTS idx_stock_movements_created ON stock_movements(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_system_alerts_type ON system_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_system_alerts_resolved ON system_alerts(resolved);

-- Insert sample data for testing
INSERT INTO products (sku_code, name, length, width, height, weight) VALUES
('SKU-TEST-001', 'Test Product 1', 10.0, 5.0, 3.0, 1.5),
('SKU-TEST-002', 'Test Product 2', 15.0, 10.0, 5.0, 2.5)
ON CONFLICT (sku_code) DO NOTHING;

INSERT INTO warehouse_locations (location_code, zone_id, row_id, shelf_id, max_volume, max_weight) VALUES
('ZONE-A-ROW-01-SHELF-01', 'ZONE-A', 'ROW-01', 'SHELF-01', 10000.0, 500.0),
('ZONE-A-ROW-01-SHELF-02', 'ZONE-A', 'ROW-01', 'SHELF-02', 10000.0, 500.0)
ON CONFLICT (location_code) DO NOTHING;

INSERT INTO packing_boxes (box_id, name, length, width, height, max_weight) VALUES
('BOX-S', 'Small Box', 20.0, 15.0, 10.0, 5.0),
('BOX-M', 'Medium Box', 30.0, 25.0, 15.0, 10.0),
('BOX-L', 'Large Box', 40.0, 30.0, 20.0, 20.0)
ON CONFLICT (box_id) DO NOTHING;

INSERT INTO shipping_carriers (carrier_id, carrier_name, api_endpoint) VALUES
('GHTK', 'Giao Hang Tiet Kiem', 'https://api.ghtk.vn'),
('GHN', 'Giao Hang Nhanh', 'https://api.ghn.vn'),
('DHL', 'DHL Express', 'https://api.dhl.com')
ON CONFLICT (carrier_id) DO NOTHING;
