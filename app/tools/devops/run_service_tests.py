"""Run service unit and integration tests tool"""

import subprocess
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.utils.error_handlers import handle_tool_error


class RunServiceTestsInput(BaseModel):
    """Input schema for run_service_tests"""
    test_suite: Optional[str] = Field("all", description="Test suite to run (all, inventory, transactions, orders, mcp, integration, security)")


class RunServiceTests(BaseTool):
    """Execute python unit and integration tests for WMS MCP Server"""
    
    name = "run_service_tests"
    description = "Execute pytest test suites for the WMS MCP Server tools and integrations to verify code correctness"
    
    def __init__(self, config):
        super().__init__(config)
        
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "test_suite": {
                    "type": "string",
                    "enum": ["all", "inventory", "transactions", "orders", "mcp", "integration", "security"],
                    "description": "Specific test suite to execute (default: all)"
                }
            }
        }
        
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        try:
            input_data = RunServiceTestsInput(**kwargs)
            suite = input_data.test_suite.lower()
            
            # Resolve directory containing the WMS MCP Server root
            # BaseTool's config should have CWD or we can find it relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            mcp_root = os.path.abspath(os.path.join(current_dir, "../../../"))
            pytest_path = os.path.join(mcp_root, ".venv/bin/pytest")
            
            # Map suite to test paths
            suite_map = {
                "inventory": "tests/test_tools/test_inventory/",
                "transactions": "tests/test_tools/test_transactions/",
                "orders": "tests/test_tools/test_orders/",
                "mcp": "tests/test_mcp/",
                "integration": "tests/test_integration/",
                "security": "tests/security/",
                "all": "tests/"
            }
            
            target_path = suite_map.get(suite, "tests/")
            full_target_path = os.path.join(mcp_root, target_path)
            
            if not os.path.exists(pytest_path):
                # Fallback to system pytest
                pytest_path = "pytest"
                
            cmd = [pytest_path, "-v", full_target_path]
            logger_msg = f"Executing: {' '.join(cmd)}"
            
            # Run test process
            # We run it with a timeout of 60 seconds to prevent hanging
            process = subprocess.run(
                cmd,
                cwd=mcp_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60
            )
            
            success = process.returncode == 0
            
            return ToolResult(
                success=True, # We return success=True because the tool ran successfully, output has test status
                data={
                    "suite": suite,
                    "target_path": target_path,
                    "passed": success,
                    "exit_code": process.returncode,
                    "output": process.stdout
                }
            )
            
        except subprocess.TimeoutExpired as te:
            return ToolResult(
                success=False,
                error="Test execution timed out after 60 seconds",
                error_code="TIMEOUT_EXPIRED",
                details={"output": te.output if hasattr(te, 'output') else ""}
            )
        except Exception as e:
            return handle_tool_error(e, self.name)
