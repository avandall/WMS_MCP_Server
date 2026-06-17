"""Main entry point for WMS MCP Server"""

import asyncio
import logging
from app.server import main as server_main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main entry point"""
    try:
        asyncio.run(server_main())
    except KeyboardInterrupt:
        print("\nShutting down WMS MCP Server...")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
