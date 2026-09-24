"""Custom exception hierarchy for WMS MCP Server."""


class WmsMcpError(Exception):
    """Base exception for all WMS MCP Server errors."""
    pass


class UpstreamServiceUnavailableError(WmsMcpError):
    """Raised when an upstream WMS Core microservice (gRPC) is unavailable or unresponsive."""
    pass
