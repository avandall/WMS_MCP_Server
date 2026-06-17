"""Input validation utilities for WMS tools"""

import re
from typing import Optional, List
from app.tools.base import ToolError


def validate_sku_code(sku_code: str) -> bool:
    """
    Validate SKU code format
    
    Args:
        sku_code: SKU code to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ToolError: If invalid
    """
    if not sku_code:
        raise ToolError(
            "SKU code cannot be empty",
            error_code="VALIDATION_ERROR",
            details={"field": "sku_code"}
        )
    
    if not isinstance(sku_code, str):
        raise ToolError(
            "SKU code must be a string",
            error_code="VALIDATION_ERROR",
            details={"field": "sku_code", "type": type(sku_code).__name__}
        )
    
    # Common SKU format: SKU-XXX-XXX or similar
    # Allow alphanumeric, hyphens, underscores
    if not re.match(r'^[A-Za-z0-9\-_]+$', sku_code):
        raise ToolError(
            f"Invalid SKU code format: {sku_code}",
            error_code="VALIDATION_ERROR",
            details={"field": "sku_code", "value": sku_code}
        )
    
    return True


def validate_location_code(location_code: str) -> bool:
    """
    Validate location code format
    
    Args:
        location_code: Location code to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ToolError: If invalid
    """
    if not location_code:
        raise ToolError(
            "Location code cannot be empty",
            error_code="VALIDATION_ERROR",
            details={"field": "location_code"}
        )
    
    if not isinstance(location_code, str):
        raise ToolError(
            "Location code must be a string",
            error_code="VALIDATION_ERROR",
            details={"field": "location_code"}
        )
    
    # Location format: ZONE-A-ROW-02-SHELF-01 or similar
    if not re.match(r'^[A-Za-z0-9\-]+$', location_code):
        raise ToolError(
            f"Invalid location code format: {location_code}",
            error_code="VALIDATION_ERROR",
            details={"field": "location_code", "value": location_code}
        )
    
    return True


def validate_quantity(quantity: int, allow_zero: bool = False) -> bool:
    """
    Validate quantity value
    
    Args:
        quantity: Quantity to validate
        allow_zero: Whether zero is allowed
        
    Returns:
        bool: True if valid
        
    Raises:
        ToolError: If invalid
    """
    if not isinstance(quantity, int):
        raise ToolError(
            "Quantity must be an integer",
            error_code="VALIDATION_ERROR",
            details={"field": "quantity", "type": type(quantity).__name__}
        )
    
    if quantity < 0:
        raise ToolError(
            "Quantity cannot be negative",
            error_code="VALIDATION_ERROR",
            details={"field": "quantity", "value": quantity}
        )
    
    if not allow_zero and quantity == 0:
        raise ToolError(
            "Quantity cannot be zero",
            error_code="VALIDATION_ERROR",
            details={"field": "quantity"}
        )
    
    return True


def validate_warehouse_id(warehouse_id: Optional[int]) -> bool:
    """
    Validate warehouse ID
    
    Args:
        warehouse_id: Warehouse ID to validate (can be None)
        
    Returns:
        bool: True if valid
        
    Raises:
        ToolError: If invalid
    """
    if warehouse_id is None:
        return True
    
    if not isinstance(warehouse_id, int):
        raise ToolError(
            "Warehouse ID must be an integer",
            error_code="VALIDATION_ERROR",
            details={"field": "warehouse_id", "type": type(warehouse_id).__name__}
        )
    
    if warehouse_id <= 0:
        raise ToolError(
            "Warehouse ID must be positive",
            error_code="VALIDATION_ERROR",
            details={"field": "warehouse_id", "value": warehouse_id}
        )
    
    return True


def validate_action(action: str, allowed_actions: List[str]) -> bool:
    """
    Validate action against allowed actions
    
    Args:
        action: Action to validate
        allowed_actions: List of allowed actions
        
    Returns:
        bool: True if valid
        
    Raises:
        ToolError: If invalid
    """
    if not action:
        raise ToolError(
            "Action cannot be empty",
            error_code="VALIDATION_ERROR",
            details={"field": "action"}
        )
    
    if action not in allowed_actions:
        raise ToolError(
            f"Invalid action: {action}. Allowed actions: {', '.join(allowed_actions)}",
            error_code="VALIDATION_ERROR",
            details={"field": "action", "value": action, "allowed": allowed_actions}
        )
    
    return True


def validate_order_id(order_id: str) -> bool:
    """
    Validate order ID format
    
    Args:
        order_id: Order ID to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ToolError: If invalid
    """
    if not order_id:
        raise ToolError(
            "Order ID cannot be empty",
            error_code="VALIDATION_ERROR",
            details={"field": "order_id"}
        )
    
    if not isinstance(order_id, str):
        raise ToolError(
            "Order ID must be a string",
            error_code="VALIDATION_ERROR",
            details={"field": "order_id"}
        )
    
    # Order ID format: ORD-XXX or similar
    if not re.match(r'^[A-Za-z0-9\-_]+$', order_id):
        raise ToolError(
            f"Invalid order ID format: {order_id}",
            error_code="VALIDATION_ERROR",
            details={"field": "order_id", "value": order_id}
        )
    
    return True


def validate_user_id(user_id: str) -> bool:
    """
    Validate user ID format
    
    Args:
        user_id: User ID to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ToolError: If invalid
    """
    if not user_id:
        raise ToolError(
            "User ID cannot be empty",
            error_code="VALIDATION_ERROR",
            details={"field": "user_id"}
        )
    
    if not isinstance(user_id, str):
        raise ToolError(
            "User ID must be a string",
            error_code="VALIDATION_ERROR",
            details={"field": "user_id"}
        )
    
    return True
