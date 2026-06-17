"""Common Pydantic models for WMS data structures"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class StockInfo(BaseModel):
    """Stock information model"""
    sku_code: str = Field(..., description="SKU code")
    warehouse_id: Optional[int] = Field(None, description="Warehouse ID")
    physical_qty: int = Field(..., description="Physical quantity on hand")
    available_qty: int = Field(..., description="Available quantity for orders")
    reserved_qty: int = Field(default=0, description="Reserved quantity")
    location_code: Optional[str] = Field(None, description="Storage location")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")


class LocationInfo(BaseModel):
    """Warehouse location information"""
    location_code: str = Field(..., description="Location code")
    zone_id: Optional[str] = Field(None, description="Zone identifier")
    row_id: Optional[str] = Field(None, description="Row identifier")
    shelf_id: Optional[str] = Field(None, description="Shelf identifier")
    max_volume: Optional[float] = Field(None, description="Maximum volume capacity")
    max_weight: Optional[float] = Field(None, description="Maximum weight capacity")
    current_volume: Optional[float] = Field(default=0, description="Current volume used")
    current_weight: Optional[float] = Field(default=0, description="Current weight used")
    available_volume: Optional[float] = Field(None, description="Available volume")
    available_weight: Optional[float] = Field(None, description="Available weight")


class MovementType(str, Enum):
    """Stock movement types"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    RETURN = "return"


class MovementRecord(BaseModel):
    """Stock movement record"""
    movement_id: Optional[str] = Field(None, description="Movement ID")
    sku_code: str = Field(..., description="SKU code")
    from_location: Optional[str] = Field(None, description="Source location")
    to_location: Optional[str] = Field(None, description="Destination location")
    quantity: int = Field(..., description="Quantity moved")
    movement_type: MovementType = Field(..., description="Type of movement")
    reference_id: Optional[str] = Field(None, description="Reference document ID")
    reason: Optional[str] = Field(None, description="Reason for movement")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="User who created the movement")


class ABCClass(str, Enum):
    """ABC classification classes"""
    A = "A"  # High value/high turnover
    B = "B"  # Medium value/turnover
    C = "C"  # Low value/turnover


class ABCClassification(BaseModel):
    """ABC classification for inventory items"""
    sku_code: str = Field(..., description="SKU code")
    abc_class: ABCClass = Field(..., description="ABC classification")
    turnover_rate: Optional[float] = Field(None, description="Annual turnover rate")
    annual_demand: Optional[int] = Field(None, description="Annual demand quantity")
    avg_order_value: Optional[float] = Field(None, description="Average order value")
    last_calculated: Optional[datetime] = Field(None, description="Last calculation timestamp")


class AlertType(str, Enum):
    """System alert types"""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class SystemAlert(BaseModel):
    """System alert model"""
    alert_id: Optional[str] = Field(None, description="Alert ID")
    alert_type: AlertType = Field(..., description="Alert type")
    message: str = Field(..., description="Alert message")
    source: Optional[str] = Field(None, description="Alert source")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    resolved: bool = Field(default=False, description="Resolution status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")


class OrderStatus(str, Enum):
    """Order status types"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PICKING = "PICKING"
    PICKED = "PICKED"
    PACKING = "PACKING"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class OrderInfo(BaseModel):
    """Order information model"""
    order_id: str = Field(..., description="Order ID")
    customer_id: Optional[str] = Field(None, description="Customer ID")
    status: OrderStatus = Field(..., description="Order status")
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Order items")
    total_quantity: int = Field(default=0, description="Total item quantity")
    total_volume: Optional[float] = Field(None, description="Total volume")
    total_weight: Optional[float] = Field(None, description="Total weight")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")


class PackingBox(BaseModel):
    """Packing box specification"""
    box_id: str = Field(..., description="Box ID")
    name: str = Field(..., description="Box name")
    length: float = Field(..., description="Length in cm")
    width: float = Field(..., description="Width in cm")
    height: float = Field(..., description="Height in cm")
    max_weight: float = Field(..., description="Maximum weight in kg")
    volume: float = Field(..., description="Volume in cubic cm")


class PickingRoute(BaseModel):
    """Picking route optimization result"""
    order_id: str = Field(..., description="Order ID")
    route: List[Dict[str, Any]] = Field(..., description="Ordered list of locations to visit")
    total_distance: Optional[float] = Field(None, description="Total distance in meters")
    estimated_time: Optional[int] = Field(None, description="Estimated time in seconds")
    optimized_at: datetime = Field(default_factory=datetime.utcnow, description="Optimization timestamp")


class PermissionAction(str, Enum):
    """Permission action types"""
    READ_STOCK = "READ_STOCK"
    UPDATE_STOCK = "UPDATE_STOCK"
    DELETE_STOCK = "DELETE_STOCK"
    MOVE_STOCK = "MOVE_STOCK"
    ADJUST_STOCK = "ADJUST_STOCK"
    MANAGE_ORDERS = "MANAGE_ORDERS"
    MANAGE_USERS = "MANAGE_USERS"
    VIEW_REPORTS = "VIEW_REPORTS"


class UserPermission(BaseModel):
    """User permission model"""
    user_id: str = Field(..., description="User ID")
    username: Optional[str] = Field(None, description="Username")
    role: Optional[str] = Field(None, description="User role")
    permissions: List[PermissionAction] = Field(default_factory=list, description="Granted permissions")
    warehouse_access: List[int] = Field(default_factory=list, description="Accessible warehouse IDs")
