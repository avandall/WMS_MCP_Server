"""DevOps and support tools category"""

from app.tools.registry import ToolRegistry
from app.tools.devops.get_container_logs import GetContainerLogs
from app.tools.devops.run_service_tests import RunServiceTests

def register_devops_tools(registry: ToolRegistry):
    """Register all devops tools"""
    registry.register(GetContainerLogs, category="devops")
    registry.register(RunServiceTests, category="devops")
