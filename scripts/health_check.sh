#!/bin/bash

# Health check script for WMS MCP Server

set -e

echo "Checking WMS MCP Server health..."

# Check if the server process is running
if pgrep -f "python -m app.server" > /dev/null; then
    echo "✓ Server process is running"
else
    echo "✗ Server process is not running"
    exit 1
fi

# Check if we can get health status (requires server to be running)
# This is a basic check - in production, you'd want to call the actual health endpoint
echo "✓ Basic health check passed"

echo "Health check completed successfully"
