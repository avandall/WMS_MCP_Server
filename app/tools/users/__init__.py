"""User management tools"""

from app.tools.registry import ToolRegistry
from app.tools.users.assign_picking_task import AssignPickingTask
from app.tools.users.audit_user_permissions import AuditUserPermissions

def register_user_tools(registry: ToolRegistry):
    """Register all user tools"""
    registry.register(AssignPickingTask, category="users")
    registry.register(AuditUserPermissions, category="users")
