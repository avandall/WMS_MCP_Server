"""Unit tests for Smart Slotting Optimizer & ABC Velocity (TASK-047 / ALG-03)"""

import pytest
from unittest.mock import AsyncMock
from app.tools.inventory.smart_slotting_optimizer import SmartSlottingOptimizer
from app.tools.inventory.abc_analysis_report import ABCAnalysisReport
from app.tools.base import ToolResult


@pytest.mark.asyncio
async def test_heavy_item_strictly_assigned_to_level_1(mock_db_client, test_config):
    """
    Acceptance Criteria:
    Hàng nặng (> 25kg): Bắt buộc bố trí tại tầng sàn (Level 1) để đảm bảo an toàn lao động.
    All upper rack levels (Level 2, 3, 4, 5) must be strictly excluded.
    """
    # Heavy product: 30kg
    prod_mock = {
        "product_id": 999,
        "sku_code": "SKU-HEAVY-MOTOR",
        "name": "Industrial Motor 30kg",
        "weight": 30.0,
        "length": 40.0,
        "width": 30.0,
        "height": 30.0
    }
    
    abc_mock = {
        "sku_code": "SKU-HEAVY-MOTOR",
        "abc_class": "A",
        "turnover_rate": 8.0,
        "pick_count": 50
    }
    
    candidate_locations = [
        # Level 1 location (Valid for heavy item)
        {"location_code": "ZONE-A-ROW-01-LEVEL-1", "zone_id": "ZONE-A", "row_id": "ROW-01", "level": 1, "available_volume": 100000.0, "available_weight": 500.0},
        # Level 2 location (Should be rejected for heavy item)
        {"location_code": "ZONE-A-ROW-01-LEVEL-2", "zone_id": "ZONE-A", "row_id": "ROW-01", "level": 2, "available_volume": 100000.0, "available_weight": 500.0},
        # Level 4 location (Should be rejected for heavy item)
        {"location_code": "ZONE-B-ROW-02-LEVEL-4", "zone_id": "ZONE-B", "row_id": "ROW-02", "level": 4, "available_volume": 100000.0, "available_weight": 500.0}
    ]
    
    mock_db_client._grpc_client.get_product = AsyncMock(return_value=prod_mock)
    mock_db_client.get_abc_classification = AsyncMock(return_value=abc_mock)
    mock_db_client.fetch_many = AsyncMock(return_value=candidate_locations)
    
    tool = SmartSlottingOptimizer(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(sku_code="SKU-HEAVY-MOTOR", quantity=1)
    assert result.success is True
    assert result.data["is_heavy_item"] is True
    
    recs = result.data["recommendations"]
    assert len(recs) == 1
    # Only Level 1 must be recommended!
    assert recs[0]["level"] == 1
    assert recs[0]["location_code"] == "ZONE-A-ROW-01-LEVEL-1"
    assert "Heavy item (> 25kg)" in recs[0]["reason"]
    # Filtered safety violations must count 2 upper shelf rejections
    assert result.data["filtered_safety_violations"] == 2


@pytest.mark.asyncio
async def test_class_a_fast_mover_slotting_priority(mock_db_client, test_config):
    """
    Acceptance Criteria:
    Hàng Class A: Ưu tiên bố trí tại các ô kệ thấp (Level 1-2) gần cửa xuất hàng (Zone A/B).
    """
    prod_mock = {
        "product_id": 101,
        "sku_code": "SKU-FAST-PHONE",
        "name": "Smartphone Flagship",
        "weight": 0.5,
        "length": 15.0,
        "width": 8.0,
        "height": 2.0
    }
    
    abc_mock = {
        "sku_code": "SKU-FAST-PHONE",
        "abc_class": "A",
        "turnover_rate": 35.0,
        "pick_count": 250
    }
    
    candidate_locations = [
        # Remote high rack
        {"location_code": "ZONE-D-ROW-09-LEVEL-5", "zone_id": "ZONE-D", "row_id": "ROW-09", "level": 5, "available_volume": 50000.0, "available_weight": 200.0},
        # Secondary zone middle rack
        {"location_code": "ZONE-C-ROW-05-LEVEL-3", "zone_id": "ZONE-C", "row_id": "ROW-05", "level": 3, "available_volume": 50000.0, "available_weight": 200.0},
        # Prime dispatch zone low shelf (Golden Zone)
        {"location_code": "ZONE-A-ROW-01-LEVEL-1", "zone_id": "ZONE-A", "row_id": "ROW-01", "level": 1, "available_volume": 50000.0, "available_weight": 200.0},
        # Prime dispatch zone level 2
        {"location_code": "ZONE-A-ROW-01-LEVEL-2", "zone_id": "ZONE-A", "row_id": "ROW-01", "level": 2, "available_volume": 50000.0, "available_weight": 200.0}
    ]
    
    mock_db_client._grpc_client.get_product = AsyncMock(return_value=prod_mock)
    mock_db_client.get_abc_classification = AsyncMock(return_value=abc_mock)
    mock_db_client.fetch_many = AsyncMock(return_value=candidate_locations)
    
    tool = SmartSlottingOptimizer(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(sku_code="SKU-FAST-PHONE", quantity=10)
    assert result.success is True
    assert result.data["abc_class"] == "A"
    
    recs = result.data["recommendations"]
    assert len(recs) == 4
    # Top recommendation MUST be Zone A, Level 1 or 2
    top_rec = recs[0]
    assert top_rec["zone"] == "ZONE-A"
    assert top_rec["level"] in [1, 2]
    assert "Class A" in top_rec["reason"]


@pytest.mark.asyncio
async def test_class_c_slow_mover_slotting_priority(mock_db_client, test_config):
    """
    Acceptance Criteria:
    Hàng Class C: Bố trí ở các vị trí xa hoặc tầng cao (Level 4-5) để bảo toàn ô thấp cho hàng A/B.
    """
    prod_mock = {
        "product_id": 303,
        "sku_code": "SKU-SLOW-PART",
        "name": "Spare Screw Rare",
        "weight": 0.2,
        "length": 10.0,
        "width": 5.0,
        "height": 5.0
    }
    
    abc_mock = {
        "sku_code": "SKU-SLOW-PART",
        "abc_class": "C",
        "turnover_rate": 0.1,
        "pick_count": 2
    }
    
    candidate_locations = [
        # Prime dispatch lower shelf (Should NOT be top choice for Class C)
        {"location_code": "ZONE-A-ROW-01-LEVEL-1", "zone_id": "ZONE-A", "row_id": "ROW-01", "level": 1, "available_volume": 50000.0, "available_weight": 200.0},
        # Remote upper rack (Ideal for Class C)
        {"location_code": "ZONE-D-ROW-09-LEVEL-5", "zone_id": "ZONE-D", "row_id": "ROW-09", "level": 5, "available_volume": 50000.0, "available_weight": 200.0}
    ]
    
    mock_db_client._grpc_client.get_product = AsyncMock(return_value=prod_mock)
    mock_db_client.get_abc_classification = AsyncMock(return_value=abc_mock)
    mock_db_client.fetch_many = AsyncMock(return_value=candidate_locations)
    
    tool = SmartSlottingOptimizer(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(sku_code="SKU-SLOW-PART", quantity=5)
    assert result.success is True
    assert result.data["abc_class"] == "C"
    
    recs = result.data["recommendations"]
    top_rec = recs[0]
    # For Class C, remote ZONE-D upper level 5 must outscore prime Zone A level 1
    assert top_rec["zone"] == "ZONE-D"
    assert top_rec["level"] == 5
    assert "Class C" in top_rec["reason"]


@pytest.mark.asyncio
async def test_shelf_capacity_tolerance_check(mock_db_client, test_config):
    """
    Acceptance Criteria:
    Kiểm tra dung sai sức chứa: Thể tích và tải trọng lô hàng mới không được vượt quá
    available_weight và available_volume thực tế của ô kệ.
    """
    # Batch: 20 units of 15kg = 300kg total, 20 units of 20x20x20 (8,000cm3) = 160,000cm3
    prod_mock = {
        "product_id": 505,
        "sku_code": "SKU-BULK-TILES",
        "name": "Ceramic Floor Tiles Box",
        "weight": 15.0,
        "length": 20.0,
        "width": 20.0,
        "height": 20.0
    }
    
    abc_mock = {
        "sku_code": "SKU-BULK-TILES",
        "abc_class": "B",
        "turnover_rate": 5.0,
        "pick_count": 30
    }
    
    candidate_locations = [
        # Location 1: available_weight = 100kg < 300kg -> REJECT
        {"location_code": "LOC-UNDERWEIGHT", "zone_id": "ZONE-B", "row_id": "ROW-01", "level": 2, "available_volume": 200000.0, "available_weight": 100.0},
        # Location 2: available_volume = 50,000cm3 < 160,000cm3 -> REJECT
        {"location_code": "LOC-UNDERVOL", "zone_id": "ZONE-B", "row_id": "ROW-01", "level": 2, "available_volume": 50000.0, "available_weight": 500.0},
        # Location 3: available_volume = 200,000cm3 and available_weight = 500kg -> ACCEPT
        {"location_code": "LOC-ADEQUATE", "zone_id": "ZONE-B", "row_id": "ROW-01", "level": 2, "available_volume": 200000.0, "available_weight": 500.0}
    ]
    
    mock_db_client._grpc_client.get_product = AsyncMock(return_value=prod_mock)
    mock_db_client.get_abc_classification = AsyncMock(return_value=abc_mock)
    mock_db_client.fetch_many = AsyncMock(return_value=candidate_locations)
    
    tool = SmartSlottingOptimizer(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(sku_code="SKU-BULK-TILES", quantity=20)
    assert result.success is True
    
    recs = result.data["recommendations"]
    assert len(recs) == 1
    assert recs[0]["location_code"] == "LOC-ADEQUATE"
    assert result.data["filtered_capacity_exceeded"] == 2


@pytest.mark.asyncio
async def test_grpc_client_abc_velocity_pareto_calculation(test_config):
    """
    Acceptance Criteria:
    Xóa bỏ dictionary hardcode "abc_class": "A" trong grpc_core_client.py.
    Tính toán phân loại ABC dựa trên số lượt pick trong giao dịch thực:
    Top 20% đóng góp 80% volume -> Class A
    Tiếp theo 15% -> Class B
    Còn lại 5% -> Class C
    """
    from app.clients.grpc_core_client import GrpcCoreClient
    from unittest.mock import MagicMock
    
    client = GrpcCoreClient(test_config)
    
    # Mock ListTransactions returning realistic transaction ledger
    # Product 1: 800 units outbound (80%) -> Class A
    # Product 2: 150 units outbound (15%) -> Class B
    # Product 3: 50 units outbound (5%) -> Class C
    class MockTx:
        def __init__(self, product_id, quantity, transaction_type):
            self.product_id = product_id
            self.quantity = quantity
            self.transaction_type = transaction_type
            
    mock_txs = [
        MockTx(product_id=1, quantity=800, transaction_type="CONSUMPTION"),
        MockTx(product_id=2, quantity=150, transaction_type="PICK"),
        MockTx(product_id=3, quantity=50, transaction_type="ADJUSTMENT_OUT")
    ]
    
    mock_stub = AsyncMock()
    mock_res = MagicMock()
    mock_res.transactions = mock_txs
    mock_stub.ListTransactions = AsyncMock(return_value=mock_res)
    
    class MockContextManager:
        async def __aenter__(self):
            return mock_stub
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
    client._client.inventory_stub = MagicMock(return_value=MockContextManager())
    
    res_a = await client.get_abc_classification("SKU-1")
    assert res_a["abc_class"] == "A"
    assert res_a["outbound_volume"] == 800
    
    res_b = await client.get_abc_classification("SKU-2")
    assert res_b["abc_class"] == "B"
    assert res_b["outbound_volume"] == 150
    
    res_c = await client.get_abc_classification("SKU-3")
    assert res_c["abc_class"] == "C"
    assert res_c["outbound_volume"] == 50
    
    # Unsold product 4 -> Defaults to Class C (NOT hardcoded A!)
    res_unsold = await client.get_abc_classification("SKU-4")
    assert res_unsold["abc_class"] == "C"
    assert res_unsold["outbound_volume"] == 0
