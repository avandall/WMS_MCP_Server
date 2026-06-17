"""Audit user permissions tool"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.clients.database_client import DatabaseClient
from app.utils.validators import validate_user_id
from app.utils.error_handlers import handle_tool_error


class AuditUserPermissionsInput(BaseModel):
    """Input schema for audit_user_permissions"""
    user_id: str = Field(..., description="User ID")
    action_required: str = Field(..., description="Action to check permissions for")


class AuditUserPermissions(BaseTool):
    """Check if user has permission to perform specific action"""
    
    name = "audit_user_permissions"
    description = "Check user permissions for specific actions to prevent unauthorized operations"
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User ID"
                },
                "action_required": {
                    "type": "string",
                    "description": "Action to check (e.g., DELETE_STOCK, UPDATE_STOCK, MANAGE_ORDERS)"
                }
            },
            "required": ["user_id", "action_required"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            # Parse input
            input_data = AuditUserPermissionsInput(**kwargs)
            
            # Validate input
            validate_user_id(input_data.user_id)
            
            # Connect to database
            await self.db.connect()
            
            # Get user info
            user_query = """
                SELECT 
                    user_id,
                    username,
                    role,
                    status,
                    warehouse_access
                FROM users
                WHERE user_id = $1
            """
            
            user_info = await self.db.fetch_one(user_query, input_data.user_id)
            
            if not user_info:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"User not found: {input_data.user_id}",
                    error_code="NOT_FOUND"
                )
            
            # Get user permissions
            permissions_query = """
                SELECT permission
                FROM user_permissions
                WHERE user_id = $1
            """
            
            user_permissions = await self.db.fetch_many(permissions_query, input_data.user_id)
            permission_list = [p['permission'] for p in user_permissions]
            
            # Get role permissions (if user has a role)
            role_permissions = []
            if user_info.get('role'):
                role_query = """
                    SELECT permission
                    FROM role_permissions
                    WHERE role = $1
                """
                role_perms = await self.db.fetch_many(role_query, user_info['role'])
                role_permissions = [p['permission'] for p in role_perms]
            
            # Close connection
            await self.db.disconnect()
            
            # Combine all permissions
            all_permissions = list(set(permission_list + role_permissions))
            
            # Check if user has the required permission
            has_permission = input_data.action_required in all_permissions
            
            # Get permission details
            permission_details = self._get_permission_details(input_data.action_required)
            
            # Security assessment
            security_assessment = self._assess_security(
                user_info, 
                has_permission, 
                input_data.action_required
            )
            
            return ToolResult(
                success=True,
                data={
                    "user_id": input_data.user_id,
                    "username": user_info.get('username'),
                    "role": user_info.get('role'),
                    "action_required": input_data.action_required,
                    "has_permission": has_permission,
                    "direct_permissions": permission_list,
                    "role_permissions": role_permissions,
                    "all_permissions": all_permissions,
                    "permission_details": permission_details,
                    "security_assessment": security_assessment,
                    "recommendation": self._generate_recommendation(has_permission, security_assessment)
                }
            )
            
        except Exception as e:
            return handle_tool_error(e, self.name)
    
    def _get_permission_details(self, action: str) -> Dict[str, Any]:
        """Get details about a specific permission"""
        permission_details = {
            "READ_STOCK": {
                "level": "LOW",
                "description": "Read-only access to stock information",
                "risk": "Low"
            },
            "UPDATE_STOCK": {
                "level": "HIGH",
                "description": "Modify stock quantities",
                "risk": "High"
            },
            "DELETE_STOCK": {
                "level": "CRITICAL",
                "description": "Delete stock records",
                "risk": "Critical"
            },
            "MOVE_STOCK": {
                "level": "MEDIUM",
                "description": "Move stock between locations",
                "risk": "Medium"
            },
            "ADJUST_STOCK": {
                "level": "HIGH",
                "description": "Adjust stock for damage/loss",
                "risk": "High"
            },
            "MANAGE_ORDERS": {
                "level": "HIGH",
                "description": "Manage order processing",
                "risk": "High"
            },
            "MANAGE_USERS": {
                "level": "CRITICAL",
                "description": "Manage user accounts and permissions",
                "risk": "Critical"
            },
            "VIEW_REPORTS": {
                "level": "LOW",
                "description": "View reports and analytics",
                "risk": "Low"
            }
        }
        
        return permission_details.get(action, {
            "level": "UNKNOWN",
            "description": "Unknown permission",
            "risk": "Unknown"
        })
    
    def _assess_security(
        self, 
        user_info: Dict[str, Any], 
        has_permission: bool, 
        action: str
    ) -> Dict[str, Any]:
        """Assess security of permission request"""
        assessment = {
            "user_status": user_info.get('status'),
            "account_active": user_info.get('status') == 'ACTIVE',
            "permission_granted": has_permission,
            "risk_level": self._get_permission_details(action).get('risk', 'Unknown'),
            "security_flags": []
        }
        
        # Add security flags
        if user_info.get('status') != 'ACTIVE':
            assessment['security_flags'].append('INACTIVE_ACCOUNT')
        
        if not has_permission:
            assessment['security_flags'].append('INSUFFICIENT_PERMISSIONS')
        
        if assessment['risk_level'] in ['HIGH', 'CRITICAL'] and not has_permission:
            assessment['security_flags'].append('HIGH_RISK_ACTION_BLOCKED')
        
        return assessment
    
    def _generate_recommendation(self, has_permission: bool, assessment: Dict[str, Any]) -> str:
        """Generate security recommendation"""
        if not assessment['account_active']:
            return "Action denied: User account is not active"
        
        if not has_permission:
            return f"Action denied: User lacks required permission. Security flags: {', '.join(assessment['security_flags'])}"
        
        if assessment['risk_level'] == 'CRITICAL':
            return "Permission granted for critical action - additional logging and monitoring recommended"
        
        return "Permission granted - action can proceed"
