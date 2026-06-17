#!/bin/bash

# Test suite runner script for WMS MCP Server

set -e

echo "========================================"
echo "WMS MCP Server Test Suite"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}pytest is not installed. Installing...${NC}"
    pip install pytest pytest-asyncio pytest-cov
fi

# Run tests with coverage
echo -e "${YELLOW}Running tests with coverage...${NC}"
pytest \
    --cov=app \
    --cov-report=html \
    --cov-report=term-missing \
    -v \
    tests/

# Check if tests passed
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
    exit 0
else
    echo -e "${RED}✗ Tests failed!${NC}"
    exit 1
fi
