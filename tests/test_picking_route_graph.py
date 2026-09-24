"""Unit tests for Warehouse Aisle Graph Routing & S-Shape Heuristic (TASK-046 / ALG-02)"""

import pytest
from app.tools.picking.generate_picking_route import GeneratePickingRoute
from app.tools.base import ToolResult


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
