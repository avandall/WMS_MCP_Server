"""Suggest packing box tool — 3D-BPP & Hazmat Segregation (TASK-045)"""

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.clients.database_client import DatabaseClient
from app.tools.base import BaseTool, ToolResult
from app.utils.error_handlers import handle_tool_error
from app.utils.validators import validate_order_id

logger = logging.getLogger(__name__)


class SuggestPackingBoxInput(BaseModel):
    """Input schema for suggest_packing_box"""
    order_id: str = Field(..., description="Order ID")


class SuggestPackingBox(BaseTool):
    """Suggest optimal packing box using 3D Bin Packing Problem (3D-BPP) with dunnage buffer and hazmat segregation"""
    
    name = "suggest_packing_box"
    description = (
        "3D Bin Packing Problem (3D-BPP) optimizer: accounts for 3D item geometry, rotation constraints, "
        "10% dunnage buffer, dimensional weight (DIM weight = L*W*H/5000), and hazmat segregation."
    )
    
    def __init__(self, config):
        super().__init__(config)
        self.db = DatabaseClient(config)
    
    def get_input_schema(self) -> dict[str, Any]:
        """Get input schema"""
        return {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Order ID"
                }
            },
            "required": ["order_id"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the 3D-BPP packing box recommendation tool"""
        try:
            input_data = SuggestPackingBoxInput(**kwargs)
            validate_order_id(input_data.order_id)
            
            await self.db.connect()
            
            # Fetch order items
            order_items = await self.db.fetch_many("SELECT order_items", input_data.order_id)
            
            if not order_items:
                doc = await self.db._grpc_client.get_document(input_data.order_id)
                if doc and doc.get("items"):
                    order_items = []
                    for item in doc["items"]:
                        prod_dim = await self.db._grpc_client.get_product(item.get("product_id", 1))
                        length = prod_dim.get("length", 20.0) if prod_dim else 20.0
                        width = prod_dim.get("width", 15.0) if prod_dim else 15.0
                        height = prod_dim.get("height", 10.0) if prod_dim else 10.0
                        weight = prod_dim.get("weight", 1.5) if prod_dim else 1.5
                        qty = item.get("quantity", 1)
                        
                        allow_rotation = prod_dim.get("allow_rotation", True) if prod_dim else True
                        hazmat_class = prod_dim.get("hazmat_class") if prod_dim else None
                        category = prod_dim.get("category", "GENERAL") if prod_dim else "GENERAL"
                        is_fragile = bool(prod_dim.get("is_fragile", False) if prod_dim else False)
                        if not is_fragile:
                            is_fragile = bool(item.get("is_fragile", False) or "FRAGILE" in str(category).upper())
                        
                        order_items.append({
                            "sku_code": item.get("sku_code", f"SKU-{item.get('product_id', 1)}"),
                            "name": prod_dim.get("name", "") if prod_dim else "",
                            "quantity": qty,
                            "length": float(length),
                            "width": float(width),
                            "height": float(height),
                            "weight": float(weight),
                            "allow_rotation": bool(allow_rotation),
                            "hazmat_class": hazmat_class,
                            "category": category,
                            "is_fragile": is_fragile,
                            "item_volume": float(length * width * height),
                            "total_weight": float(weight * qty)
                        })
            
            if not order_items:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"No items found for order: {input_data.order_id}",
                    error_code="NOT_FOUND"
                )
            
            # Ensure each item has necessary fields with defaults
            sanitized_items = []
            for it in order_items:
                l = float(it.get("length", 20.0))
                w = float(it.get("width", 15.0))
                h = float(it.get("height", 10.0))
                wt = float(it.get("weight", 1.0))
                q = int(it.get("quantity", 1))
                allow_rot = it.get("allow_rotation", True)
                hazmat = it.get("hazmat_class")
                cat = it.get("category", "GENERAL")
                name = it.get("name", "")
                is_frag = bool(it.get("is_fragile", False) or "FRAGILE" in str(cat).upper())
                
                sanitized_items.append({
                    "sku_code": it.get("sku_code", "UNKNOWN"),
                    "name": name,
                    "quantity": q,
                    "length": l,
                    "width": w,
                    "height": h,
                    "weight": wt,
                    "allow_rotation": allow_rot,
                    "hazmat_class": hazmat,
                    "category": cat,
                    "is_fragile": is_frag,
                    "item_volume": l * w * h,
                    "total_weight": wt * q
                })
            
            # 1. Check Hazmat Incompatibility Segregation
            is_compatible, conflict_msg = self._check_hazmat_segregation(sanitized_items)
            if not is_compatible:
                await self.db.disconnect()
                return ToolResult(
                    success=False,
                    error=f"Hazmat Segregation Violation: {conflict_msg}",
                    error_code="HAZMAT_INCOMPATIBILITY",
                    data={
                        "order_id": input_data.order_id,
                        "hazmat_incompatible": True,
                        "conflict_detail": conflict_msg
                    }
                )
            
            # Calculate aggregate statistics
            total_volume = sum(item["item_volume"] * item["quantity"] for item in sanitized_items)
            total_weight = sum(item["total_weight"] for item in sanitized_items)
            
            # Fetch candidate boxes
            available_boxes = await self._get_available_boxes()
            await self.db.disconnect()
            
            # 2. Run 3D-BPP Geometric Packing & DIM Weight Optimization
            recommendations = self._find_optimal_boxes_3d(
                sanitized_items,
                total_volume,
                total_weight,
                available_boxes,
                dunnage_buffer=0.10
            )
            
            # If no candidate box can accommodate all items, return OVERSIZED_ITEM error (TASK-062 / MED-10)
            if not recommendations:
                return ToolResult(
                    success=False,
                    error_code="OVERSIZED_ITEM",
                    error="Order contains oversized items exceeding all available carton dimensions. Palletizing / custom crate required.",
                    data={
                        "order_id": input_data.order_id,
                        "order_items": sanitized_items,
                        "total_volume_cm3": round(total_volume, 2),
                        "total_weight_kg": round(total_weight, 2),
                        "item_count": len(sanitized_items),
                        "available_box_count": len(available_boxes)
                    }
                )

            return ToolResult(
                success=True,
                data={
                    "order_id": input_data.order_id,
                    "order_items": sanitized_items,
                    "total_volume_cm3": round(total_volume, 2),
                    "total_weight_kg": round(total_weight, 2),
                    "item_count": len(sanitized_items),
                    "dunnage_buffer_percent": 10.0,
                    "recommendations": recommendations,
                    "selected_recommendation": recommendations[0] if recommendations else None
                }
            )
            
        except Exception as e:  # noqa: BLE001
            return handle_tool_error(e, self.name)
    
    def _check_hazmat_segregation(self, items: list[dict[str, Any]]) -> tuple[bool, str]:
        """
        Check if any hazardous materials are mixed with food, beverage, or electronics in the same carton.
        Acceptance Criteria: Ngăn chặn việc đóng chung sản phẩm hazmat_class với thực phẩm hoặc đồ điện tử.
        """
        has_hazmat = False
        hazmat_names = []
        has_food = False
        food_names = []
        has_electronics = False
        electronics_names = []
        
        for item in items:
            h_class = item.get("hazmat_class")
            cat = str(item.get("category", "")).upper()
            name = str(item.get("name", "")).lower()
            
            # Hazmat check
            if h_class or "hazmat" in cat or "chemical" in cat or "hazmat" in name:
                has_hazmat = True
                hazmat_names.append(item.get("sku_code"))
            
            # Food check
            if "FOOD" in cat or "BEVERAGE" in cat or any(w in name for w in ["food", "beverage", "drink", "milk", "snack"]):
                has_food = True
                food_names.append(item.get("sku_code"))
                
            # Electronics check
            if "ELECTRONIC" in cat or any(w in name for w in ["electronic", "phone", "laptop", "battery", "tablet", "pc"]):
                has_electronics = True
                electronics_names.append(item.get("sku_code"))
        
        if has_hazmat and has_food:
            return False, f"Cannot co-pack Hazmat items ({', '.join(hazmat_names)}) with Food products ({', '.join(food_names)}) in the same box."
        
        if has_hazmat and has_electronics:
            return False, f"Cannot co-pack Hazmat items ({', '.join(hazmat_names)}) with Electronic products ({', '.join(electronics_names)}) in the same box."
            
        return True, ""
    
    async def _get_available_boxes(self) -> list[dict[str, Any]]:
        """Get available packing box sizes"""
        boxes = await self.db.fetch_many("SELECT packing_boxes")
        if boxes:
            return boxes
        return [
            {"box_id": 1, "name": "Small Box (S)", "length": 25.0, "width": 20.0, "height": 15.0, "max_weight": 5.0, "volume": 7500.0},
            {"box_id": 2, "name": "Medium Box (M)", "length": 40.0, "width": 30.0, "height": 25.0, "max_weight": 15.0, "volume": 30000.0},
            {"box_id": 3, "name": "Large Box (L)", "length": 60.0, "width": 40.0, "height": 35.0, "max_weight": 30.0, "volume": 84000.0},
            {"box_id": 4, "name": "Extra Large Box (XL)", "length": 80.0, "width": 60.0, "height": 50.0, "max_weight": 50.0, "volume": 240000.0},
            {"box_id": 5, "name": "Long Heavy Box (XXL)", "length": 140.0, "width": 40.0, "height": 30.0, "max_weight": 50.0, "volume": 168000.0}
        ]
    
    def _find_optimal_boxes_3d(
        self,
        items: list[dict[str, Any]],
        total_volume: float,
        total_weight: float,
        available_boxes: list[dict[str, Any]],
        dunnage_buffer: float = 0.10
    ) -> list[dict[str, Any]]:
        """
        Evaluate candidate boxes using:
        1. Dunnage buffer (10% linear allowance deduction on box dimensions)
        2. 3D-BPP Geometric Packing check with rotation constraints (Extreme Points / First-Fit Decreasing 3D)
        3. Weight limit check
        4. Dimensional Weight (DIM Weight = L*W*H / 5000) & Billable Weight optimization
        """
        recommendations = []
        
        for box in available_boxes:
            box_l = float(box.get("length", 0.0))
            box_w = float(box.get("width", 0.0))
            box_h = float(box.get("height", 0.0))
            max_weight = float(box.get("max_weight", 0.0))
            box_volume = float(box.get("volume", box_l * box_w * box_h))
            
            # Check weight constraint
            if max_weight < total_weight:
                continue
            
            # Usable dimensions with 10% dunnage buffer deducted
            usable_l = box_l * (1.0 - dunnage_buffer)
            usable_w = box_w * (1.0 - dunnage_buffer)
            usable_h = box_h * (1.0 - dunnage_buffer)
            usable_volume = usable_l * usable_w * usable_h
            
            if usable_volume < total_volume:
                continue
            
            # 3D Bin Packing Check
            fits_in_box = self._can_pack_items_3d(items, usable_l, usable_w, usable_h)
            if not fits_in_box:
                continue
            
            # Calculate DIM Weight and Billable Weight
            # DIM Weight standard formula: (L * W * H) / 5000 in cm and kg
            dim_weight = (box_l * box_w * box_h) / 5000.0
            billable_weight = max(total_weight, dim_weight)
            
            wasted_space = box_volume - total_volume
            efficiency = (total_volume / box_volume) * 100.0 if box_volume > 0 else 0.0
            
            # Recommendation score: higher efficiency, lower wasted space, lower billable weight
            score = efficiency - (wasted_space / 10000.0) - (billable_weight * 0.5)
            
            recommendations.append({
                "box_id": box.get("box_id"),
                "name": box.get("name"),
                "dimensions": {
                    "length": box_l,
                    "width": box_w,
                    "height": box_h
                },
                "usable_dimensions": {
                    "length": round(usable_l, 2),
                    "width": round(usable_w, 2),
                    "height": round(usable_h, 2)
                },
                "volume_cm3": box_volume,
                "usable_volume_cm3": round(usable_volume, 2),
                "max_weight_kg": max_weight,
                "gross_weight_kg": round(total_weight, 2),
                "dim_weight_kg": round(dim_weight, 2),
                "billable_weight_kg": round(billable_weight, 2),
                "efficiency_percent": round(efficiency, 2),
                "wasted_space_cm3": round(wasted_space, 2),
                "recommendation_score": round(score, 2)
            })
        
        # Sort recommendations: lowest billable weight first, then highest efficiency
        recommendations.sort(key=lambda x: (x["billable_weight_kg"], -x["efficiency_percent"], -x["recommendation_score"]))
        return recommendations[:5]
    
    def _has_sufficient_base_support(
        self,
        item: Any,
        placement: tuple[float, float, float, float, float, float],
        placed_boxes: list[Any],
        min_ratio: float = 0.70
    ) -> bool:
        """Check base support ratio and fragile item stacking constraints.

        Acceptance Criteria (TASK-062):
        1. If pz == 0: perfectly supported by the carton bottom -> True.
        2. If pz > 0: must have at least 70% (min_ratio) of base area (dx * dy)
           supported by the top surfaces (z' + dz' == pz) of placed boxes below.
        3. Never place an item with weight > 2.0kg on top of any placed box with is_fragile=True.
        """
        return _has_sufficient_base_support(item, placement, placed_boxes, min_ratio=min_ratio)

    def _can_pack_items_3d(
        self,
        items: list[dict[str, Any]],
        box_l: float,
        box_w: float,
        box_h: float
    ) -> bool:
        """
        Check if all items fit into the 3D box under rotation constraints.
        Implements Extreme Points 3D placement algorithm with gravity & base support constraints.
        """
        # Flatten individual unit items
        expanded_items: list[dict[str, Any]] = []
        for it in items:
            qty = max(1, int(it.get("quantity", 1)))
            for _ in range(qty):
                expanded_items.append({
                    "sku_code": it.get("sku_code"),
                    "length": float(it.get("length", 0.0)),
                    "width": float(it.get("width", 0.0)),
                    "height": float(it.get("height", 0.0)),
                    "weight": float(it.get("weight", 0.0)),
                    "is_fragile": bool(it.get("is_fragile", False)),
                    "allow_rotation": bool(it.get("allow_rotation", True)),
                    "volume": float(it.get("length", 0.0)) * float(it.get("width", 0.0)) * float(it.get("height", 0.0))
                })
        
        # Sort items in First-Fit Decreasing order (TASK-062: sturdy non-fragile & heavier items first)
        expanded_items.sort(
            key=lambda x: (
                not x.get("is_fragile", False),
                x.get("weight", 0.0),
                x["volume"],
                max(x["length"], x["width"], x["height"])
            ),
            reverse=True
        )
        
        # Placed boxes list: [(px, py, pz, dx, dy, dz, item_dict)]
        placed_boxes: list[Any] = []
        
        # Candidate extreme points: list of (x, y, z)
        extreme_points: list[tuple[float, float, float]] = [(0.0, 0.0, 0.0)]
        
        for item in expanded_items:
            l, w, h = item["length"], item["width"], item["height"]
            allow_rotation = item["allow_rotation"]
            
            # Determine valid orientations
            if allow_rotation:
                # 6 possible orthogonal orientations
                orientations = list({
                    (l, w, h), (l, h, w),
                    (w, l, h), (w, h, l),
                    (h, l, w), (h, w, l)
                })
            else:
                # Must stay upright: Z axis is locked to height 'h', can only rotate around Z
                orientations = list({
                    (l, w, h),
                    (w, l, h)
                })
            
            # Try to place item at the best extreme point
            placed = False
            for ep in extreme_points:
                px, py, pz = ep
                for (dx, dy, dz) in orientations:
                    # Check box boundary constraints
                    if (px + dx <= box_l + 1e-5) and (py + dy <= box_w + 1e-5) and (pz + dz <= box_h + 1e-5):
                        # Check collision/overlap with already placed boxes
                        overlap = False
                        for b in placed_boxes:
                            ox, oy, oz, odx, ody, odz = b[:6]
                            if not (
                                (px + dx <= ox + 1e-5) or (ox + odx <= px + 1e-5) or
                                (py + dy <= oy + 1e-5) or (oy + ody <= py + 1e-5) or
                                (pz + dz <= oz + 1e-5) or (oz + odz <= pz + 1e-5)
                            ):
                                overlap = True
                                break
                        
                        if overlap:
                            continue

                        # Check base support & gravity & fragile constraints (TASK-062)
                        if not self._has_sufficient_base_support(item, (px, py, pz, dx, dy, dz), placed_boxes, min_ratio=0.70):
                            continue
                        
                        # Valid placement found
                        placed_boxes.append((px, py, pz, dx, dy, dz, item))
                        placed = True
                        
                        # Generate new candidate extreme points
                        new_points = [
                            (px + dx, py, pz),
                            (px, py + dy, pz),
                            (px, py, pz + dz)
                        ]
                        
                        # Filter extreme points within box limits
                        extreme_points.remove(ep)
                        for np in new_points:
                            if np[0] < box_l and np[1] < box_w and np[2] < box_h and np not in extreme_points:
                                extreme_points.append(np)
                        
                        # Sort extreme points (prefer lower Z, then lower Y, then lower X)
                        extreme_points.sort(key=lambda p: (p[2], p[1], p[0]))
                        break
                if placed:
                    break
            
            if not placed:
                return False
        
        return True


def _has_sufficient_base_support(
    item: Any,
    placement: tuple[float, float, float, float, float, float],
    placed_boxes: list[Any],
    min_ratio: float = 0.70
) -> bool:
    """Check base support ratio and fragile item stacking constraints (TASK-062).

    1. Base Support & Gravity:
       - If pz <= 0: resting on carton bottom -> 100% support (True).
       - If pz > 0: must have at least min_ratio (70%) of base area (dx * dy)
         supported by top surfaces (z' + dz' == pz) of placed boxes below.
    2. Fragile Item Protection:
       - Never place an item with weight > 2.0kg on top of any placed box marked is_fragile=True.
    """
    px, py, pz, dx, dy, _dz = placement
    if pz <= 1e-5:
        return True

    base_area = dx * dy
    if base_area <= 1e-5:
        return False

    item_weight = 0.0
    if isinstance(item, dict):
        item_weight = float(item.get("weight", 0.0))
    elif hasattr(item, "weight"):
        item_weight = float(getattr(item, "weight", 0.0))

    supported_area = 0.0
    for b in placed_boxes:
        if isinstance(b, (tuple, list)):
            ox, oy, oz, odx, ody, odz = b[0], b[1], b[2], b[3], b[4], b[5]
            placed_item = b[6] if len(b) > 6 else {}
        elif isinstance(b, dict):
            ox = float(b.get("x", b.get("px", 0.0)))
            oy = float(b.get("y", b.get("py", 0.0)))
            oz = float(b.get("z", b.get("pz", 0.0)))
            odx = float(b.get("dx", b.get("length", 0.0)))
            ody = float(b.get("dy", b.get("width", 0.0)))
            odz = float(b.get("dz", b.get("height", 0.0)))
            placed_item = b
        else:
            ox = float(getattr(b, "x", 0.0))
            oy = float(getattr(b, "y", 0.0))
            oz = float(getattr(b, "z", 0.0))
            odx = float(getattr(b, "dx", 0.0))
            ody = float(getattr(b, "dy", 0.0))
            odz = float(getattr(b, "dz", 0.0))
            placed_item = b

        # Check if the placed box directly touches candidate item's bottom surface
        if abs((oz + odz) - pz) <= 1e-5:
            x_overlap = max(0.0, min(px + dx, ox + odx) - max(px, ox))
            y_overlap = max(0.0, min(py + dy, oy + ody) - max(py, oy))
            overlap = x_overlap * y_overlap

            if overlap > 1e-5:
                # Fragile constraint check:
                # Tuyệt đối không xếp kiện hàng có trọng lượng > 2.0kg đè lên kiện hàng có thuộc tính is_fragile=True
                is_box_fragile = False
                if isinstance(placed_item, dict):
                    is_box_fragile = bool(placed_item.get("is_fragile", False))
                elif hasattr(placed_item, "is_fragile"):
                    is_box_fragile = bool(getattr(placed_item, "is_fragile", False))

                if is_box_fragile and item_weight > 2.0:
                    return False

                supported_area += overlap

    support_ratio = supported_area / base_area
    return support_ratio + 1e-5 >= min_ratio

