"""Unit tests for Warehouse Aisle Graph Routing & S-Shape Heuristic (TASK-046 / ALG-02)"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.tools.picking.generate_picking_route import GeneratePickingRoute
from app.tools.base import ToolResult
from app.clients.grpc_core_client import GrpcCoreClient


@pytest.mark.asyncio
async def test_aisle_rectilinear_distance_vs_euclidean_through_steel_rack(test_config):
    """
    Acceptance Criteria:
    Đường đi của nhân viên giữa 2 ô kệ đối lưng nhau qua kệ sắt phải có quãng đường >= 2 * khoảng cách ra đầu dãy,
    tuyệt đối không được bằng bề dày kệ (Euclidean xuyên kệ).
    
    Example:
    Loc 1: Aisle 1 (x=0, y=25)
    Loc 2: Aisle 2 (x=2, y=25) across a 2-meter thick steel rack in a 50m long aisle.
    Euclidean distance would be sqrt((2-0)^2 + (25-25)^2) = 2.0m (walking through 5 tons of steel!).
    Real Aisle distance requires walking 25m to front (y=0) or back (y=50), crossing 2m, and walking 25m back:
    dist = 25 + 2 + 25 = 52.0m >= 50m (2 * 25m).
    """
    tool = GeneratePickingRoute(test_config)
    
    loc1 = {"x": 0.0, "y": 25.0}
    loc2 = {"x": 2.0, "y": 25.0}
    
    real_dist = tool.calculate_aisle_distance(loc1, loc2, cross_front_y=0.0, cross_back_y=50.0)
    
    # Must NOT equal Euclidean distance (2.0m)
    assert real_dist != 2.0
    # Must equal 52.0m
    assert real_dist == 52.0
    # Strictly >= 2 * 25m (half-aisle distance to cross aisle)
    assert real_dist >= 50.0


@pytest.mark.asyncio
async def test_s_shape_serpentine_route_order(mock_db_client, test_config):
    """
    Test S-Shape (Serpentine) Heuristic across 2 aisles:
    Aisle 1 (x=3.0) with picks at y=10.0 and y=40.0.
    Aisle 2 (x=6.0) with picks at y=15.0 and y=35.0.
    
    Route must:
    1. Start at DEPOT (0, 0)
    2. Enter Aisle 1 from front (y=0) -> pick y=10 -> pick y=40 -> exit at back (y=50)
    3. Enter Aisle 2 from back (y=50) -> pick y=35 -> pick y=15 -> exit at front (y=0)
    4. End at PACK-STATION (0, 0)
    """
    items_mock = [
        {
            "sku_code": "SKU-A1-1",
            "quantity": 1,
            "weight_kg": 2.0,
            "location_code": "LOC-A1-1",
            "x_coordinate": 3.0,
            "y_coordinate": 10.0
        },
        {
            "sku_code": "SKU-A1-2",
            "quantity": 1,
            "weight_kg": 2.0,
            "location_code": "LOC-A1-2",
            "x_coordinate": 3.0,
            "y_coordinate": 40.0
        },
        {
            "sku_code": "SKU-A2-1",
            "quantity": 1,
            "weight_kg": 2.0,
            "location_code": "LOC-A2-1",
            "x_coordinate": 6.0,
            "y_coordinate": 15.0
        },
        {
            "sku_code": "SKU-A2-2",
            "quantity": 1,
            "weight_kg": 2.0,
            "location_code": "LOC-A2-2",
            "x_coordinate": 6.0,
            "y_coordinate": 35.0
        }
    ]
    
    mock_db_client.fetch_many.return_value = items_mock
    
    tool = GeneratePickingRoute(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-SSHAPE-01")
    assert result.success is True
    
    trips = result.data["trips"]
    assert len(trips) == 1
    route = trips[0]["route"]
    
    # Verify sequence:
    # 1. DEPOT
    assert route[0]["location_code"] == "DEPOT"
    # In Aisle 1 (x=3), moving forward (Y ASC): y=10, then y=40
    assert route[1]["location_code"] == "LOC-A1-1"
    assert route[1]["y"] == 10.0
    assert route[2]["location_code"] == "LOC-A1-2"
    assert route[2]["y"] == 40.0
    
    # In Aisle 2 (x=6), moving downward from back cross-aisle (Y DESC): y=35, then y=15
    assert route[3]["location_code"] == "LOC-A2-2"
    assert route[3]["y"] == 35.0
    assert route[4]["location_code"] == "LOC-A2-1"
    assert route[4]["y"] == 15.0
    
    # Last stop: PACK-STATION
    assert route[5]["location_code"] == "PACK-STATION"


@pytest.mark.asyncio
async def test_multi_trip_partitioning_exceeding_cart_capacity(mock_db_client, test_config):
    """
    Acceptance Criteria:
    Tích hợp kiểm tra tải trọng xe đẩy: Nếu tổng cân nặng đơn hàng vượt quá tải trọng xe (vd 60kg),
    thuật toán phải chia thành nhiều chuyến nhặt (Multi-Trip Pick Route).
    """
    # 3 heavy items of 25kg each -> Total weight = 75kg > 60kg cart limit
    heavy_items_mock = [
        {
            "sku_code": "SKU-HEAVY-1",
            "quantity": 1,
            "weight_kg": 25.0,
            "total_weight_kg": 25.0,
            "location_code": "LOC-HEAVY-1",
            "x_coordinate": 3.0,
            "y_coordinate": 10.0
        },
        {
            "sku_code": "SKU-HEAVY-2",
            "quantity": 1,
            "weight_kg": 25.0,
            "total_weight_kg": 25.0,
            "location_code": "LOC-HEAVY-2",
            "x_coordinate": 3.0,
            "y_coordinate": 20.0
        },
        {
            "sku_code": "SKU-HEAVY-3",
            "quantity": 1,
            "weight_kg": 25.0,
            "total_weight_kg": 25.0,
            "location_code": "LOC-HEAVY-3",
            "x_coordinate": 6.0,
            "y_coordinate": 15.0
        }
    ]
    
    mock_db_client.fetch_many.return_value = heavy_items_mock
    
    tool = GeneratePickingRoute(test_config)
    tool.db = mock_db_client
    
    # Cart capacity limit = 60.0kg
    result = await tool.execute(order_id="ORD-MULTI-TRIP", max_cart_capacity_kg=60.0)
    assert result.success is True
    assert result.data["multi_trip"] is True
    
    trips = result.data["trips"]
    assert len(trips) == 2  # Trip 1: 50kg (2 items), Trip 2: 25kg (1 item)
    
    assert trips[0]["total_weight_kg"] == 50.0
    assert trips[0]["total_weight_kg"] <= 60.0
    assert trips[0]["route"][0]["location_code"] == "DEPOT"
    assert trips[0]["route"][-1]["location_code"] == "PACK-STATION"
    
    assert trips[1]["total_weight_kg"] == 25.0
    assert trips[1]["total_weight_kg"] <= 60.0
    assert trips[1]["route"][0]["location_code"] == "DEPOT"
    assert trips[1]["route"][-1]["location_code"] == "PACK-STATION"


@pytest.mark.asyncio
async def test_depot_and_pack_station_enforcement(mock_db_client, test_config):
    """
    Acceptance Criteria:
    Lộ trình bắt buộc bắt đầu từ Depot (tọa độ xe đẩy) -> nhặt tuần tự -> kết thúc tại PackStation (bàn đóng gói).
    """
    item_mock = [
        {
            "sku_code": "SKU-SINGLE",
            "quantity": 1,
            "weight_kg": 5.0,
            "location_code": "LOC-AISLE1",
            "x_coordinate": 3.0,
            "y_coordinate": 15.0
        }
    ]
    mock_db_client.fetch_many.return_value = item_mock
    
    tool = GeneratePickingRoute(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-SINGLE-STOP")
    assert result.success is True
    
    trips = result.data["trips"]
    assert len(trips) == 1
    route = trips[0]["route"]
    
    # Must start at DEPOT and finish at PACK-STATION
    assert route[0]["location_code"] == "DEPOT"
    assert route[0]["type"] == "DEPOT"
    assert route[-1]["location_code"] == "PACK-STATION"
    assert route[-1]["type"] == "PACK_STATION"


@pytest.mark.asyncio
async def test_grpc_client_preserves_real_spatial_coordinates_without_modulo(test_config):
    """
    Acceptance Criteria (TASK-055 / CRIT-01):
    Xóa bỏ hoàn toàn float(loc.position_id * 2 % 50) và float(loc.position_id * 3 % 50).
    Đọc trực tiếp loc.x_coordinate, loc.y_coordinate, loc.z_coordinate, loc.aisle, loc.bay, loc.level.
    """
    client = GrpcCoreClient(test_config)

    class MockLocation:
        def __init__(self, id, warehouse_id, position_id, product_id, lpn, quantity,
                     allocated_qty, available_qty, status, lot_number, location_code,
                     x_coordinate, y_coordinate, z_coordinate, zone_id, aisle, bay, level):
            self.id = id
            self.warehouse_id = warehouse_id
            self.position_id = position_id
            self.product_id = product_id
            self.lpn = lpn
            self.quantity = quantity
            self.allocated_qty = allocated_qty
            self.available_qty = available_qty
            self.status = status
            self.lot_number = lot_number
            self.location_code = location_code
            self.x_coordinate = x_coordinate
            self.y_coordinate = y_coordinate
            self.z_coordinate = z_coordinate
            self.zone_id = zone_id
            self.aisle = aisle
            self.bay = bay
            self.level = level

    # If position_id is 10:
    # Old modulo would give: x = 10 * 2 % 50 = 20.0, y = 10 * 3 % 50 = 30.0
    # Real warehouse position has: x = 14.5, y = 42.0, z = 3.5
    real_mock_loc = MockLocation(
        id=1, warehouse_id=1, position_id=10, product_id=101, lpn="LPN-001",
        quantity=50, allocated_qty=0, available_qty=50, status="AVAILABLE", lot_number="LOT-01",
        location_code="ZONE-A-A02-B04-L3",
        x_coordinate=14.5, y_coordinate=42.0, z_coordinate=3.5,
        zone_id="ZONE-A", aisle="AISLE-02", bay="BAY-04", level="3"
    )

    mock_stub = AsyncMock()
    mock_res = MagicMock()
    mock_res.locations = [real_mock_loc]
    mock_stub.GetInventoryLocations = AsyncMock(return_value=mock_res)

    class MockContextManager:
        async def __aenter__(self):
            return mock_stub
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    client._client.inventory_stub = MagicMock(return_value=MockContextManager())

    results = await client.get_inventory_locations()
    assert len(results) == 1
    loc = results[0]

    # Verify real coordinates are preserved without modulo
    assert loc["x_coordinate"] == 14.5
    assert loc["y_coordinate"] == 42.0
    assert loc["z_coordinate"] == 3.5
    assert loc["location_code"] == "ZONE-A-A02-B04-L3"
    assert loc["aisle"] == "AISLE-02"
    assert loc["bay"] == "BAY-04"
    assert loc["level"] == "3"


@pytest.mark.asyncio
async def test_generate_picking_route_uses_real_grpc_coordinates(mock_db_client, test_config):
    """
    Acceptance Criteria (TASK-055 / CRIT-01):
    Lộ trình generate_picking_route phản ánh chính xác khoảng cách giữa các tọa độ thực tế của kho bãi.
    """
    mock_db_client.fetch_many.return_value = []  # Force fetch via gRPC

    mock_doc = {
        "order_id": "ORD-REAL-COORD",
        "items": [
            {"product_id": 1, "sku_code": "SKU-REAL-1", "quantity": 2},
            {"product_id": 2, "sku_code": "SKU-REAL-2", "quantity": 1}
        ]
    }
    real_locations = [
        {
            "id": 1,
            "product_id": 1,
            "location_code": "ZONE-A-A01-B02",
            "x_coordinate": 3.0,
            "y_coordinate": 12.0,
            "z_coordinate": 1.0,
            "zone_id": "ZONE-A",
            "row_id": "ROW-01",
            "shelf_id": "SHELF-02"
        },
        {
            "id": 2,
            "product_id": 2,
            "location_code": "ZONE-A-A02-B05",
            "x_coordinate": 6.0,
            "y_coordinate": 38.0,
            "z_coordinate": 1.0,
            "zone_id": "ZONE-A",
            "row_id": "ROW-02",
            "shelf_id": "SHELF-05"
        }
    ]

    mock_db_client._grpc_client.get_document = AsyncMock(return_value=mock_doc)
    mock_db_client._grpc_client.get_inventory_locations = AsyncMock(return_value=real_locations)
    mock_db_client._grpc_client.get_product = AsyncMock(return_value={"weight": 2.0, "length": 10, "width": 10, "height": 10})

    tool = GeneratePickingRoute(test_config)
    tool.db = mock_db_client

    result = await tool.execute(order_id="ORD-REAL-COORD")
    assert result.success is True

    trips = result.data["trips"]
    assert len(trips) == 1
    route = trips[0]["route"]

    # Confirm coordinates in route match real coordinates
    pick_stops = [s for s in route if s.get("type") == "PICK"]
    assert len(pick_stops) == 2
    assert pick_stops[0]["x"] == 3.0
    assert pick_stops[0]["y"] == 12.0
    assert pick_stops[1]["x"] == 6.0
    assert pick_stops[1]["y"] == 38.0


@pytest.mark.asyncio
async def test_one_way_aisle_rule_enforcement(mock_db_client, test_config):
    """
    Acceptance Criteria (TASK-066 / DOM-01):
    Khi enforce_one_way = True (mặc định):
    - Trong dãy lẻ (Aisle 1, 3, ...): Các điểm nhặt hàng bắt buộc sắp xếp theo tọa độ Y tăng dần (Y1 <= Y2 <= ...) (Front -> Back).
    - Trong dãy chẵn (Aisle 2, 4, ...): Các điểm nhặt hàng bắt buộc sắp xếp theo tọa độ Y giảm dần (Y1 >= Y2 >= ...) (Back -> Front).
    - Triệt tiêu 100% nguy cơ xe nâng đi đối đầu trong lối đi hẹp (VNA).
    """
    # 3 aisles with scrambled pick items:
    # Aisle 1 (Odd): y=35, y=10, y=25 -> Must become: 10, 25, 35 (ASC)
    # Aisle 2 (Even): y=15, y=40, y=28 -> Must become: 40, 28, 15 (DESC)
    # Aisle 3 (Odd): y=48, y=8 -> Must become: 8, 48 (ASC)
    items_mock = [
        # Aisle 1 (Odd)
        {"sku_code": "SKU-A1-35", "quantity": 1, "weight_kg": 1.0, "location_code": "ZONE-A-A01-B07", "aisle": "AISLE-01", "x_coordinate": 3.0, "y_coordinate": 35.0},
        {"sku_code": "SKU-A1-10", "quantity": 1, "weight_kg": 1.0, "location_code": "ZONE-A-A01-B02", "aisle": "AISLE-01", "x_coordinate": 3.0, "y_coordinate": 10.0},
        {"sku_code": "SKU-A1-25", "quantity": 1, "weight_kg": 1.0, "location_code": "ZONE-A-A01-B05", "aisle": "AISLE-01", "x_coordinate": 3.0, "y_coordinate": 25.0},
        # Aisle 2 (Even)
        {"sku_code": "SKU-A2-15", "quantity": 1, "weight_kg": 1.0, "location_code": "ZONE-A-A02-B03", "aisle": "AISLE-02", "x_coordinate": 6.0, "y_coordinate": 15.0},
        {"sku_code": "SKU-A2-40", "quantity": 1, "weight_kg": 1.0, "location_code": "ZONE-A-A02-B08", "aisle": "AISLE-02", "x_coordinate": 6.0, "y_coordinate": 40.0},
        {"sku_code": "SKU-A2-28", "quantity": 1, "weight_kg": 1.0, "location_code": "ZONE-A-A02-B06", "aisle": "AISLE-02", "x_coordinate": 6.0, "y_coordinate": 28.0},
        # Aisle 3 (Odd)
        {"sku_code": "SKU-A3-48", "quantity": 1, "weight_kg": 1.0, "location_code": "ZONE-A-A03-B09", "aisle": "AISLE-03", "x_coordinate": 9.0, "y_coordinate": 48.0},
        {"sku_code": "SKU-A3-08", "quantity": 1, "weight_kg": 1.0, "location_code": "ZONE-A-A03-B01", "aisle": "AISLE-03", "x_coordinate": 9.0, "y_coordinate": 8.0},
    ]

    mock_db_client.fetch_many.return_value = items_mock

    tool = GeneratePickingRoute(test_config)
    tool.db = mock_db_client

    # Execute with enforce_one_way=True (explicit and default)
    result = await tool.execute(order_id="ORD-ONE-WAY-01", enforce_one_way=True)
    assert result.success is True
    assert result.data["route_metrics"]["enforce_one_way"] is True

    route = result.data["trips"][0]["route"]
    picks = [s for s in route if s.get("type") == "PICK"]
    assert len(picks) == 8

    # Extract picks by aisle
    a1_picks = [p for p in picks if p["x"] == 3.0]
    a2_picks = [p for p in picks if p["x"] == 6.0]
    a3_picks = [p for p in picks if p["x"] == 9.0]

    assert len(a1_picks) == 3
    assert len(a2_picks) == 3
    assert len(a3_picks) == 2

    # Verification: Aisle 1 (Odd) is strictly Y ASCENDING (10 -> 25 -> 35)
    a1_y = [p["y"] for p in a1_picks]
    assert a1_y == [10.0, 25.0, 35.0]
    for idx in range(len(a1_y) - 1):
        assert a1_y[idx] <= a1_y[idx + 1], f"Aisle 1 violation: {a1_y}"

    # Verification: Aisle 2 (Even) is strictly Y DESCENDING (40 -> 28 -> 15)
    a2_y = [p["y"] for p in a2_picks]
    assert a2_y == [40.0, 28.0, 15.0]
    for idx in range(len(a2_y) - 1):
        assert a2_y[idx] >= a2_y[idx + 1], f"Aisle 2 violation: {a2_y}"

    # Verification: Aisle 3 (Odd) is strictly Y ASCENDING (8 -> 48)
    a3_y = [p["y"] for p in a3_picks]
    assert a3_y == [8.0, 48.0]
    for idx in range(len(a3_y) - 1):
        assert a3_y[idx] <= a3_y[idx + 1], f"Aisle 3 violation: {a3_y}"


@pytest.mark.asyncio
async def test_one_way_aisle_rule_schema_and_defaults(test_config):
    """Verify input schema reflects enforce_one_way=True by default."""
    tool = GeneratePickingRoute(test_config)
    schema = tool.get_input_schema()
    props = schema["properties"]
    assert "enforce_one_way" in props
    assert props["enforce_one_way"]["type"] == "boolean"
    assert props["enforce_one_way"]["default"] is True
    assert "is_batch_pick" in props
    assert props["is_batch_pick"]["type"] == "boolean"
    assert props["is_batch_pick"]["default"] is False


# ==============================================================================
# TASK-069: Put-Wall Sortation in Batch Picking (DOM-04)
# ==============================================================================

@pytest.mark.asyncio
async def test_sortation_wall_in_batch_picking_route(mock_db_client, test_config):
    """
    Acceptance Criteria (TASK-069 / DOM-04):
    Thêm điểm dừng SORTATION_WALL trước PACK-STATION khi is_batch_pick = True.
    Tính toán khoảng cách và thời gian di chuyển bao gồm cả chặng phân loại Put-Wall.
    """
    items_mock = [
        {
            "sku_code": "SKU-BATCH-01",
            "quantity": 5,
            "weight_kg": 1.0,
            "location_code": "LOC-A1-1",
            "x_coordinate": 3.0,
            "y_coordinate": 15.0
        },
        {
            "sku_code": "SKU-BATCH-02",
            "quantity": 10,
            "weight_kg": 0.5,
            "location_code": "LOC-A2-1",
            "x_coordinate": 6.0,
            "y_coordinate": 20.0
        }
    ]
    mock_db_client.fetch_many.return_value = items_mock

    tool = GeneratePickingRoute(test_config)
    tool.db = mock_db_client

    # 1. Execute with is_batch_pick = True
    result_batch = await tool.execute(
        order_id="ORD-BATCH-WAVE-01",
        is_batch_pick=True,
        sortation_wall_x=0.0,
        sortation_wall_y=10.0
    )
    assert result_batch.success is True
    data = result_batch.data
    assert data["route_metrics"]["is_batch_pick"] is True
    assert data["route_metrics"]["has_sortation_wall"] is True

    route = data["trips"][0]["route"]
    location_codes = [s["location_code"] for s in route]

    # Verify SORTATION_WALL exists and is positioned immediately before PACK-STATION
    assert "SORTATION_WALL" in location_codes
    assert "PACK-STATION" in location_codes
    sort_idx = location_codes.index("SORTATION_WALL")
    pack_idx = location_codes.index("PACK-STATION")
    assert pack_idx == sort_idx + 1

    # Verify stop details
    sort_stop = route[sort_idx]
    assert sort_stop["type"] == "SORTATION_WALL"
    assert sort_stop["zone_id"] == "SORTATION"
    assert sort_stop["x"] == 0.0
    assert sort_stop["y"] == 10.0
    assert "Put-Wall" in sort_stop["instruction"]

    # 2. Execute with is_batch_pick = False (Standard single-order picking)
    result_std = await tool.execute(
        order_id="ORD-STANDARD-01",
        is_batch_pick=False
    )
    assert result_std.success is True
    std_data = result_std.data
    assert std_data["route_metrics"]["is_batch_pick"] is False
    assert std_data["route_metrics"]["has_sortation_wall"] is False

    std_route = std_data["trips"][0]["route"]
    std_location_codes = [s["location_code"] for s in std_route]
    assert "SORTATION_WALL" not in std_location_codes
    assert "PACK-STATION" in std_location_codes

    # The batch route should include extra distance walking to the Put-Wall
    # Put-Wall is at (0, 10), Pack Station at (0, 0)
    assert data["route_metrics"]["total_distance_m"] > std_data["route_metrics"]["total_distance_m"]


# ==============================================================================
# TASK-085: Safe Waypoints for One-Way Aisle Transitions (DOM-04)
# ==============================================================================

@pytest.mark.asyncio
async def test_one_way_aisle_waypoints_between_even_aisles(mock_db_client, test_config):
    """
    Acceptance Criteria (TASK-085 / DOM-04):
    Khi xe nâng kết thúc ở Dãy 2 tại đầu Front (Y = 0), điểm nhặt tiếp theo ở Dãy 4 bắt buộc phải vào từ đầu Back (Y = 50).
    - Trong generate_picking_route.py, khi curr_y != target_entry_y, thuật toán sinh ít nhất 1 Waypoint chuyển tiếp
      (is_waypoint=True, type="WAYPOINT", zone_id="CORRIDOR") đánh dấu hành lang an toàn.
    - Lộ trình chuyển từ Dãy 2 sang Dãy 4 có chứa điểm trung chuyển hành lang, không nhảy cóc trực tiếp tọa độ.
    - Triệt tiêu hoàn toàn nguy cơ đi ngược chiều hoặc đâm va trong VNA.
    """
    items_mock = [
        # Dãy 2 (Even): x=6.0, Y descending (Back -> Front)
        {
            "sku_code": "SKU-A2-40",
            "quantity": 1,
            "weight_kg": 2.0,
            "location_code": "ZONE-A-A02-B08",
            "aisle": "AISLE-02",
            "x_coordinate": 6.0,
            "y_coordinate": 40.0
        },
        {
            "sku_code": "SKU-A2-10",
            "quantity": 1,
            "weight_kg": 2.0,
            "location_code": "ZONE-A-A02-B02",
            "aisle": "AISLE-02",
            "x_coordinate": 6.0,
            "y_coordinate": 10.0
        },
        # Dãy 4 (Even): x=12.0, Y descending (Back -> Front)
        {
            "sku_code": "SKU-A4-45",
            "quantity": 1,
            "weight_kg": 2.0,
            "location_code": "ZONE-A-A04-B09",
            "aisle": "AISLE-04",
            "x_coordinate": 12.0,
            "y_coordinate": 45.0
        },
        {
            "sku_code": "SKU-A4-20",
            "quantity": 1,
            "weight_kg": 2.0,
            "location_code": "ZONE-A-A04-B04",
            "aisle": "AISLE-04",
            "x_coordinate": 12.0,
            "y_coordinate": 20.0
        }
    ]

    mock_db_client.fetch_many.return_value = items_mock

    tool = GeneratePickingRoute(test_config)
    tool.db = mock_db_client

    result = await tool.execute(order_id="ORD-WAYPOINT-01", enforce_one_way=True)
    assert result.success is True

    trips = result.data["trips"]
    assert len(trips) == 1
    route = trips[0]["route"]

    # 1. Verify that waypoints exist with is_waypoint=True
    waypoints = [s for s in route if s.get("is_waypoint") is True]
    assert len(waypoints) >= 1, "Must generate at least 1 transition waypoint"
    for wp in waypoints:
        assert wp.get("type") == "WAYPOINT"
        assert wp.get("zone_id") == "CORRIDOR"

    # 2. Find the transition between last pick in Aisle 2 and first pick in Aisle 4
    # Last pick in Aisle 2: ZONE-A-A02-B02 (y=10.0)
    # First pick in Aisle 4: ZONE-A-A04-B09 (y=45.0)
    stop_codes = [s["location_code"] for s in route]
    a2_last_idx = stop_codes.index("ZONE-A-A02-B02")
    a4_first_idx = stop_codes.index("ZONE-A-A04-B09")

    assert a4_first_idx > a2_last_idx + 1, "Route must NOT jump directly from Aisle 2 to Aisle 4 without corridor waypoints!"

    # Slice intermediate stops between A2 and A4
    transition_stops = route[a2_last_idx + 1 : a4_first_idx]
    transition_codes = [s["location_code"] for s in transition_stops]

    # Verify transition contains Front corridor exit, Perimeter bypass corridor, and Aisle 4 Back entry
    assert "CORRIDOR-FRONT" in transition_codes
    assert "CORRIDOR-PERIMETER" in transition_codes
    assert "CORRIDOR-ENTRY-AISLE-04" in transition_codes

    # 3. Verify each transition stop has is_waypoint=True and valid coordinates
    for st in transition_stops:
        assert st.get("is_waypoint") is True
        assert st.get("type") == "WAYPOINT"
        assert st.get("zone_id") == "CORRIDOR"

    # 4. Verify coordinate continuity during transition:
    # Aisle 2 exit: Front (y=0) -> Perimeter bypass (y=50) -> Aisle 4 Back entrance (y=50)
    corridor_front = next(s for s in transition_stops if s["location_code"] == "CORRIDOR-FRONT")
    assert corridor_front["y"] == 0.0
    assert corridor_front["x"] == 6.0  # at Aisle 2 exit

    corridor_perimeter = next(s for s in transition_stops if s["location_code"] == "CORRIDOR-PERIMETER")
    assert corridor_perimeter["y"] == 50.0  # moved up to Back cross-aisle
    assert corridor_perimeter["x"] >= 12.0  # perimeter lane outside racking

    corridor_entry_a4 = next(s for s in transition_stops if s["location_code"] == "CORRIDOR-ENTRY-AISLE-04")
    assert corridor_entry_a4["y"] == 50.0  # entry at Back of Aisle 4
    assert corridor_entry_a4["x"] == 12.0  # aligned with Aisle 4

    # 5. Verify instructions for waypoints exist in trip instructions
    instructions = trips[0]["instructions"]
    wp_instructions = [ins for ins in instructions if ins.get("is_waypoint") is True]
    assert len(wp_instructions) >= len(transition_stops)
    for ins in wp_instructions:
        assert "Navigate via" in ins["instruction"] or "corridor" in ins["instruction"].lower() or "safely" in ins["instruction"].lower()



