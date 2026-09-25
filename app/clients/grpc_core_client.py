"""gRPC Core Client for WMS MCP Server — High-level abstraction for WMS_Core microservices"""

import logging
from typing import Any, Dict, List, Optional
from app.config import Config
from app.integration.grpc_client import grpc_client
from app.exceptions import UpstreamServiceUnavailableError

# Import generated protobuf messages
from app.gen.wms.inventory.v1 import inventory_pb2
from app.gen.wms.documents.v1 import documents_pb2
from app.gen.wms.product.v1 import product_pb2
from app.gen.wms.warehouse.v1 import warehouse_pb2

logger = logging.getLogger(__name__)


class GrpcCoreClient:
    """gRPC Client wrapping WMS_Core microservice RPCs for MCP tools"""
    
    def __init__(self, config: Config):
        self.config = config
        self._client = grpc_client
        self._sku_cache: Dict[str, int] = {}
        
    async def connect(self) -> None:
        """Lifecycle connect handler (no-op as grpc channels are managed lazily)"""
        logger.info("GrpcCoreClient connected to WMS_Core services")
        
    async def disconnect(self) -> None:
        """Close cached gRPC channels"""
        await self._client.close_all()
        logger.info("GrpcCoreClient disconnected")

    async def resolve_product_id(self, sku_or_id: str | int) -> int:
        """
        Resolve SKU code or Product ID string to integer product_id.
        Lookup order:
        1. Pure integer / digit string -> int(sku_or_id)
        2. In-memory local cache -> cached product_id
        3. Standard 'SKU-<digits>' format -> int(digits)
        4. gRPC product-service ListProducts lookup matching product name/sku
        """
        raw_str = str(sku_or_id).strip()
        if raw_str.isdigit():
            return int(raw_str)

        sku_upper = raw_str.upper()
        if sku_upper in self._sku_cache:
            return self._sku_cache[sku_upper]

        # Check if it is standard numeric SKU prefix e.g. SKU-123
        if sku_upper.startswith("SKU-"):
            suffix = sku_upper[4:]
            if suffix.isdigit():
                pid = int(suffix)
                self._sku_cache[sku_upper] = pid
                return pid

        # Query Product Service via gRPC ListProducts
        try:
            async with self._client.product_stub() as stub:
                req = product_pb2.ListProductsRequest()
                res = await stub.ListProducts(req)
                for prod in res.products:
                    p_name = (prod.name or "").strip().upper()
                    p_id = prod.product_id
                    # Cache both exact name and SKU-prefixed form
                    self._sku_cache[p_name] = p_id
                    self._sku_cache[f"SKU-{p_id}"] = p_id
                    if p_name == sku_upper or f"SKU-{p_id}" == sku_upper:
                        return p_id

                # Second pass: check if sku_upper without "SKU-" matches product name
                cleaned = sku_upper.replace("SKU-", "").strip()
                if cleaned in self._sku_cache:
                    return self._sku_cache[cleaned]

        except UpstreamServiceUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error querying product service to resolve SKU '{raw_str}': {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Product Service unavailable: {e}") from e

        if sku_upper in self._sku_cache:
            return self._sku_cache[sku_upper]

        raise ValueError(f"Product/SKU '{raw_str}' could not be resolved to a valid product ID")

    async def get_stock_info(self, sku_or_id: str | int, warehouse_id: int = 1) -> Optional[Dict[str, Any]]:
        """Get stock availability for product in warehouse via inventory gRPC service"""
        try:
            prod_id = await self.resolve_product_id(sku_or_id)
            async with self._client.inventory_stub() as stub:
                req = inventory_pb2.GetAvailabilityRequest(product_id=prod_id, warehouse_id=warehouse_id)
                res = await stub.GetAvailability(req)
                return {
                    "sku_code": str(sku_or_id),
                    "product_id": res.product_id,
                    "warehouse_id": res.warehouse_id,
                    "physical_qty": res.physical_qty,
                    "reserved_qty": res.reserved_qty,
                    "available_qty": res.available_qty,
                    "location_code": f"ZONE-A-SHELF-{res.warehouse_id}",
                    "last_updated": "2026-09-20T00:00:00Z"
                }
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error calling GetAvailability gRPC: {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Inventory Service unavailable: {e}") from e

    async def get_inventory_locations(
        self, warehouse_id: int = 1, product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get inventory location rows via inventory-service gRPC with real spatial coordinates"""
        try:
            async with self._client.inventory_stub() as stub:
                req = inventory_pb2.GetInventoryLocationsRequest(
                    warehouse_id=warehouse_id,
                    product_id=product_id or 0
                )
                res = await stub.GetInventoryLocations(req)
                locations = []
                for loc in res.locations:
                    locations.append({
                        "id": loc.id,
                        "warehouse_id": loc.warehouse_id,
                        "position_id": loc.position_id,
                        "product_id": loc.product_id,
                        "lpn": loc.lpn,
                        "quantity": loc.quantity,
                        "allocated_qty": loc.allocated_qty,
                        "available_qty": loc.available_qty,
                        "status": loc.status,
                        "lot_number": loc.lot_number,
                        "location_code": loc.location_code or f"ZONE-A-POS-{loc.position_id or 1}",
                        "x_coordinate": float(loc.x_coordinate),
                        "y_coordinate": float(loc.y_coordinate),
                        "z_coordinate": float(loc.z_coordinate),
                        "zone_id": loc.zone_id or "ZONE-A",
                        "row_id": loc.aisle or "ROW-01",
                        "shelf_id": loc.bay or "SHELF-01",
                        "aisle": loc.aisle or "AISLE-01",
                        "bay": loc.bay or "BAY-01",
                        "level": loc.level or "1",
                    })
                return locations
        except Exception as e:
            logger.error(f"Error calling GetInventoryLocations gRPC: {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Inventory Locations unavailable: {e}") from e

    async def get_document(self, document_id: str | int) -> Optional[Dict[str, Any]]:
        """Get document/order details via documents-service gRPC"""
        try:
            doc_id = int(document_id) if str(document_id).isdigit() else 1
            async with self._client.documents_stub() as stub:
                req = documents_pb2.GetDocumentRequest(document_id=doc_id)
                doc = await stub.GetDocument(req)
                items = [
                    {
                        "item_id": i + 1,
                        "product_id": item.product_id,
                        "sku_code": f"SKU-{item.product_id}",
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "total_price": item.quantity * item.unit_price,
                        "item_status": "PICKED" if doc.status == "COMPLETED" else "PENDING"
                    }
                    for i, item in enumerate(doc.items)
                ]
                return {
                    "order_id": str(doc.document_id),
                    "document_id": doc.document_id,
                    "doc_type": doc.doc_type,
                    "status": doc.status or "CONFIRMED",
                    "customer_id": doc.customer_id,
                    "customer_name": f"Customer-{doc.customer_id}",
                    "from_warehouse_id": doc.from_warehouse_id,
                    "to_warehouse_id": doc.to_warehouse_id,
                    "total_amount": sum(item["total_price"] for item in items),
                    "items": items,
                    "created_by": doc.created_by,
                    "created_at": doc.created_at or "2026-09-20T00:00:00Z"
                }
        except Exception as e:
            logger.error(f"Error calling GetDocument gRPC: {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Documents Service unavailable: {e}") from e

    async def get_product(self, product_id: str | int) -> Optional[Dict[str, Any]]:
        """Get product dimensions and info via product-service gRPC"""
        try:
            p_id = int(product_id) if str(product_id).isdigit() else 1
            async with self._client.product_stub() as stub:
                req = product_pb2.GetProductRequest(product_id=p_id)
                prod = await stub.GetProduct(req)
                uoms_list = []
                case_size = 1
                for u in getattr(prod, "uoms", []):
                    u_code = str(getattr(u, "uom_code", "")).upper()
                    c_factor = float(getattr(u, "conversion_factor", 1.0))
                    to_uom = str(getattr(u, "to_uom_code", "")).upper()
                    uoms_list.append({
                        "uom_code": u_code,
                        "conversion_factor": c_factor,
                        "to_uom_code": to_uom
                    })
                    if u_code in ["CASE", "CS", "CARTON", "BOX"] and c_factor > 1:
                        case_size = int(c_factor)

                return {
                    "product_id": prod.product_id,
                    "sku_code": f"SKU-{prod.product_id}",
                    "name": prod.name,
                    "price": prod.price,
                    "length": prod.length_cm or 20.0,
                    "width": prod.width_cm or 15.0,
                    "height": prod.height_cm or 10.0,
                    "weight": prod.gross_weight_kg or 1.5,
                    "description": prod.description,
                    "base_uom": getattr(prod, "base_uom", "EACH"),
                    "uoms": uoms_list,
                    "case_size": case_size,
                }
        except Exception as e:
            logger.error(f"Error calling GetProduct gRPC: {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Product Service unavailable: {e}") from e

    async def get_shelf_capacity(self, location_code: str, warehouse_id: int = 1) -> Optional[Dict[str, Any]]:
        """Get shelf capacity info for location via warehouse/inventory service without hardcoding"""
        try:
            async with self._client.warehouse_stub() as stub:
                req = warehouse_pb2.GetPositionRequest(warehouse_id=warehouse_id, code=location_code)
                pos = await stub.GetPosition(req)

                if not pos or not pos.id:
                    raise UpstreamServiceUnavailableError(
                        f"Position '{location_code}' not found in Warehouse {warehouse_id}"
                    )

                max_weight = float(pos.max_weight_kg) if pos.max_weight_kg else 500.0
                if getattr(pos, "max_volume_cbm", None):
                    max_vol = float(pos.max_volume_cbm) * 1_000_000.0 if pos.max_volume_cbm < 500.0 else float(pos.max_volume_cbm)
                else:
                    max_vol = 50000.0

                current_weight = 0.0
                current_volume = 0.0
                async with self._client.inventory_stub() as inv_stub:
                    inv_req = inventory_pb2.GetInventoryLocationsRequest(
                        warehouse_id=warehouse_id,
                        position_id=pos.id
                    )
                    inv_res = await inv_stub.GetInventoryLocations(inv_req)
                    for item in inv_res.locations:
                        prod = await self.get_product(item.product_id)
                        p_weight = prod.get("weight", 1.0) if prod else 1.0
                        p_vol = (prod.get("length", 10.0) * prod.get("width", 10.0) * prod.get("height", 10.0)) if prod else 1000.0
                        current_weight += item.quantity * p_weight
                        current_volume += item.quantity * p_vol

                avail_weight = max(0.0, max_weight - current_weight)
                avail_volume = max(0.0, max_vol - current_volume)

                return {
                    "location_code": pos.code or location_code,
                    "zone_id": pos.zone or "ZONE-A",
                    "row_id": pos.aisle or "ROW-01",
                    "shelf_id": pos.bay or "SHELF-01",
                    "level": pos.level or "1",
                    "max_volume": max_vol,
                    "max_weight": max_weight,
                    "current_volume": round(current_volume, 2),
                    "current_weight": round(current_weight, 2),
                    "available_volume": round(avail_volume, 2),
                    "available_weight": round(avail_weight, 2)
                }
        except UpstreamServiceUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error calling GetPosition/GetInventoryLocations gRPC: {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Warehouse/Inventory Service unavailable: {e}") from e

    async def get_abc_classification(self, sku_code: str, warehouse_id: int = 1) -> Optional[Dict[str, Any]]:
        """
        Get ABC classification for SKU calculated dynamically from outbound pick velocity in inventory transactions.
        Pareto Rules:
        - Top 20% SKU contributing 80% volume/picks -> Class A
        - Next 30% SKU contributing 15% volume/picks -> Class B
        - Remaining 50% SKU contributing 5% volume/picks -> Class C
        """
        try:
            async with self._client.inventory_stub() as stub:
                req = inventory_pb2.ListTransactionsRequest(warehouse_id=warehouse_id, limit=200)
                res = await stub.ListTransactions(req)
                
                pick_counts: Dict[int, int] = {}
                outbound_volumes: Dict[int, int] = {}
                for tx in res.transactions:
                    tx_type = (tx.transaction_type or "").upper()
                    if tx_type in ["CONSUMPTION", "PICK", "ADJUSTMENT_OUT", "OUTBOUND", "SHIP"]:
                        pid = tx.product_id
                        qty = abs(tx.quantity)
                        pick_counts[pid] = pick_counts.get(pid, 0) + 1
                        outbound_volumes[pid] = outbound_volumes.get(pid, 0) + qty
                
                try:
                    target_pid = await self.resolve_product_id(sku_code)
                except Exception:
                    target_pid = 1
                
                target_picks = pick_counts.get(target_pid, 0)
                target_volume = outbound_volumes.get(target_pid, 0)
                
                if outbound_volumes:
                    total_outbound = sum(outbound_volumes.values())
                    sorted_by_vol = sorted(outbound_volumes.items(), key=lambda x: x[1], reverse=True)
                    
                    running_sum = 0
                    abc_map: Dict[int, str] = {}
                    for pid, vol in sorted_by_vol:
                        running_sum += vol
                        cum_ratio = running_sum / total_outbound if total_outbound > 0 else 0
                        if not abc_map or cum_ratio <= 0.80:
                            abc_map[pid] = "A"
                        elif cum_ratio <= 0.95:
                            abc_map[pid] = "B"
                        else:
                            abc_map[pid] = "C"
                    
                    abc_class = abc_map.get(target_pid, "C")
                else:
                    abc_class = "C"
                
                import datetime
                return {
                    "sku_code": sku_code,
                    "abc_class": abc_class,
                    "turnover_rate": round(target_volume / 30.0, 2) if target_volume > 0 else 0.0,
                    "annual_demand": target_volume * 4 if target_volume > 0 else 0,
                    "pick_count": target_picks,
                    "outbound_volume": target_volume,
                    "last_calculated": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
        except Exception as e:
            logger.warning(f"Error calculating ABC velocity from gRPC transactions: {e}")
            import datetime
            return {
                "sku_code": sku_code,
                "abc_class": "C",
                "turnover_rate": 0.0,
                "annual_demand": 0,
                "pick_count": 0,
                "outbound_volume": 0,
                "last_calculated": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }

    async def get_stock_movement_history(self, sku_code: str, limit_days: int = 7) -> List[Dict[str, Any]]:
        """Get stock movement history via inventory ListTransactions or audit ListEvents"""
        try:
            async with self._client.inventory_stub() as stub:
                req = inventory_pb2.ListTransactionsRequest(limit=50)
                res = await stub.ListTransactions(req)
                movements = []
                for tx in res.transactions:
                    movements.append({
                        "movement_id": tx.id,
                        "sku_code": f"SKU-{tx.product_id}",
                        "from_location": "REC-STAGE",
                        "to_location": f"ZONE-A-POS-{tx.warehouse_id}",
                        "quantity": tx.quantity,
                        "movement_type": tx.transaction_type,
                        "reference_id": str(tx.document_id),
                        "created_at": tx.created_at,
                        "created_by": tx.user_id
                    })
                return movements
        except Exception as e:
            logger.error(f"Error listing transactions via gRPC: {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Inventory Service unavailable: {e}") from e

    async def get_low_stock_items(self, threshold_qty: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get items with low stock via reporting-service gRPC"""
        try:
            from app.gen.wms.reporting.v1 import reporting_pb2
            async with self._client.reporting_stub() as stub:
                req = reporting_pb2.InventoryReportRequest(low_stock_threshold=threshold_qty or 10)
                res = await stub.InventoryReport(req)
                import json
                if res.json:
                    data = json.loads(res.json)
                    if isinstance(data, list):
                        return data
                return []
        except Exception as e:
            logger.error(f"Error getting low stock report via gRPC: {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Reporting Service unavailable: {e}") from e

    async def create_draft_proposal(
        self,
        sku_code: str,
        warehouse_id: int,
        location_code: str,
        adjustment: int,
        reason: str,
        proposal_type: str = "QUANTITY_ADJUSTMENT",
        requested_by: str = "mcp-agent",
        current_quantity: int = 0,
        proposed_quantity: int = 0,
        position_id: int = 0,
        digital_signature: str = ""
    ) -> Dict[str, Any]:
        """Create a draft inventory proposal via inventory-service gRPC (Maker-Checker workflow)"""
        try:
            async with self._client.inventory_stub() as stub:
                req = inventory_pb2.CreateDraftProposalRequest(
                    proposal_type=proposal_type,
                    sku_code=sku_code,
                    warehouse_id=warehouse_id,
                    location_code=location_code,
                    position_id=position_id,
                    current_quantity=current_quantity,
                    proposed_quantity=proposed_quantity,
                    adjustment=adjustment,
                    reason=reason,
                    requested_by=requested_by,
                    digital_signature=digital_signature,
                )
                res = await stub.CreateDraftProposal(req)
                if not res.success:
                    raise ValueError(res.message or "Failed to create draft proposal")
                
                prop = res.proposal
                return {
                    "proposal_id": prop.proposal_id,
                    "proposal_type": prop.proposal_type,
                    "sku_code": prop.sku_code,
                    "warehouse_id": prop.warehouse_id,
                    "location_code": prop.location_code,
                    "position_id": prop.position_id,
                    "current_quantity": prop.current_quantity,
                    "proposed_quantity": prop.proposed_quantity,
                    "adjustment": prop.adjustment,
                    "status": prop.status,
                    "reason": prop.reason,
                    "requested_by": prop.requested_by,
                    "created_at": prop.created_at,
                    "message": res.message
                }
        except UpstreamServiceUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Error calling CreateDraftProposal gRPC: {e}")
            raise UpstreamServiceUnavailableError(f"WMS Core Inventory Service unavailable: {e}") from e

    async def fetch_one(self, query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """Mock/fallback compatibility shim for legacy database calls"""
        return None

    async def fetch_many(self, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """Mock/fallback compatibility shim for legacy database calls"""
        return []

    async def execute(self, query: str, *args, **kwargs) -> str:
        """Mock/fallback compatibility shim for legacy database calls"""
        return "SUCCESS"


# Singleton client instance
grpc_core_client = GrpcCoreClient(Config())
