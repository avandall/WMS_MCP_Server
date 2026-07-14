"""gRPC client integration for WMS Core services"""

import logging
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager
import grpc

from app.config import get_config

# Import generated stubs
from app.gen.wms.identity.v1 import identity_pb2_grpc
from app.gen.wms.customer.v1 import customer_pb2_grpc
from app.gen.wms.product.v1 import product_pb2_grpc
from app.gen.wms.warehouse.v1 import warehouse_pb2_grpc
from app.gen.wms.inventory.v1 import inventory_pb2_grpc
from app.gen.wms.documents.v1 import documents_pb2_grpc
from app.gen.wms.audit.v1 import audit_pb2_grpc
from app.gen.wms.reporting.v1 import reporting_pb2_grpc
from app.gen.wms.ai.v1 import ai_pb2_grpc

logger = logging.getLogger(__name__)


class WMSGrpcClient:
    """Async gRPC client with connection pooling/caching for WMS Core services"""
    
    def __init__(self):
        self.config = get_config()
        self._channels: Dict[str, grpc.aio.Channel] = {}
        
    def _get_addr(self, service_name: str) -> str:
        """Get the service address from configuration"""
        addr_map = {
            "identity": self.config.IDENTITY_GRPC_ADDR,
            "customer": self.config.CUSTOMER_GRPC_ADDR,
            "product": self.config.PRODUCT_GRPC_ADDR,
            "warehouse": self.config.WAREHOUSE_GRPC_ADDR,
            "inventory": self.config.INVENTORY_GRPC_ADDR,
            "documents": self.config.DOCUMENTS_GRPC_ADDR,
            "audit": self.config.AUDIT_GRPC_ADDR,
            "reporting": self.config.REPORTING_GRPC_ADDR,
            "ai": self.config.AI_GRPC_ADDR,
        }
        return addr_map.get(service_name, f"{service_name}-service:50051")
        
    async def get_channel(self, service_name: str) -> grpc.aio.Channel:
        """Get or create an async gRPC channel for a service"""
        if service_name not in self._channels:
            addr = self._get_addr(service_name)
            logger.info(f"Creating async gRPC channel to {service_name} at {addr}")
            
            # Simple insecure channel for dev/local.
            # Production could load certs and use secure_channel based on config.
            channel = grpc.aio.insecure_channel(addr)
            self._channels[service_name] = channel
            
        return self._channels[service_name]
        
    async def close_all(self):
        """Close all cached gRPC channels"""
        for service_name, channel in list(self._channels.items()):
            logger.info(f"Closing gRPC channel for {service_name}")
            await channel.close()
        self._channels.clear()

    @asynccontextmanager
    async def identity_stub(self):
        channel = await self.get_channel("identity")
        yield identity_pb2_grpc.IdentityServiceStub(channel)

    @asynccontextmanager
    async def customer_stub(self):
        channel = await self.get_channel("customer")
        yield customer_pb2_grpc.CustomerServiceStub(channel)

    @asynccontextmanager
    async def product_stub(self):
        channel = await self.get_channel("product")
        yield product_pb2_grpc.ProductServiceStub(channel)

    @asynccontextmanager
    async def warehouse_stub(self):
        channel = await self.get_channel("warehouse")
        yield warehouse_pb2_grpc.WarehouseServiceStub(channel)

    @asynccontextmanager
    async def warehouse_ops_stub(self):
        channel = await self.get_channel("warehouse")
        yield warehouse_pb2_grpc.WarehouseOperationsServiceStub(channel)

    @asynccontextmanager
    async def inventory_stub(self):
        channel = await self.get_channel("inventory")
        yield inventory_pb2_grpc.InventoryServiceStub(channel)

    @asynccontextmanager
    async def documents_stub(self):
        channel = await self.get_channel("documents")
        yield documents_pb2_grpc.DocumentsServiceStub(channel)

    @asynccontextmanager
    async def audit_stub(self):
        channel = await self.get_channel("audit")
        yield audit_pb2_grpc.AuditServiceStub(channel)

    @asynccontextmanager
    async def reporting_stub(self):
        channel = await self.get_channel("reporting")
        yield reporting_pb2_grpc.ReportingServiceStub(channel)

    @asynccontextmanager
    async def ai_stub(self):
        channel = await self.get_channel("ai")
        yield ai_pb2_grpc.AIServiceStub(channel)


# Singleton instance to be shared across tools
grpc_client = WMSGrpcClient()

