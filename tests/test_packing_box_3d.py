"""Unit tests for 3D-BPP Geometric Packing & Hazmat Segregation (TASK-045 / ALG-01)"""

import pytest

from app.tools.orders.suggest_packing_box import (
    SuggestPackingBox,
    _has_sufficient_base_support,
)


@pytest.mark.asyncio
async def test_extreme_item_120cm_vs_small_box_40cm(mock_db_client, test_config):
    """
    Test extreme case: Guitar/Golf club 120cm x 15cm x 10cm (Volume = 18,000 cm3)
    must NOT fit in a 40cm x 30cm x 25cm box (Volume = 30,000 cm3) despite box volume being larger!
    It must pick a box with length >= 120cm + 10% buffer (e.g. 140cm).
    """
    guitar_item = [
        {
            "sku_code": "SKU-GUITAR-01",
            "quantity": 1,
            "length": 120.0,
            "width": 15.0,
            "height": 10.0,
            "weight": 4.0,
            "allow_rotation": True,
            "category": "GENERAL"
        }
    ]
    
    candidate_boxes = [
        {
            "box_id": "BOX-M",
            "name": "Medium Box (M)",
            "length": 40.0,
            "width": 30.0,
            "height": 25.0,
            "max_weight": 15.0,
            "volume": 30000.0
        },
        {
            "box_id": "BOX-L",
            "name": "Large Box (L)",
            "length": 60.0,
            "width": 40.0,
            "height": 35.0,
            "max_weight": 30.0,
            "volume": 84000.0
        },
        {
            "box_id": "BOX-XXL-LONG",
            "name": "Long Heavy Box (XXL)",
            "length": 140.0,
            "width": 40.0,
            "height": 30.0,
            "max_weight": 50.0,
            "volume": 168000.0
        }
    ]
    
    mock_db_client.fetch_many.side_effect = [
        guitar_item,
        candidate_boxes
    ]
    
    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-GUITAR-01")
    assert result.success is True
    recs = result.data["recommendations"]
    assert len(recs) == 1
    # Only the 140cm long box fits the 120cm guitar
    assert recs[0]["box_id"] == "BOX-XXL-LONG"
    # BOX-M and BOX-L must be completely rejected geometrically
    box_ids = [r["box_id"] for r in recs]
    assert "BOX-M" not in box_ids
    assert "BOX-L" not in box_ids


@pytest.mark.asyncio
async def test_liquid_item_rotation_restricted(mock_db_client, test_config):
    """
    Test liquid/beverage bottle (height=32cm, length=8cm, width=8cm) with allow_rotation=False.
    If rotation were allowed, it could fit lying down in a box with height=25cm, length=40cm, width=30cm.
    Because allow_rotation=False, it cannot be turned horizontally and must reject boxes with usable height < 32cm!
    """
    bottle_item = [
        {
            "sku_code": "SKU-BEVERAGE-SYRUP",
            "name": "Syrup Glass Bottle",
            "quantity": 1,
            "length": 8.0,
            "width": 8.0,
            "height": 32.0,
            "weight": 1.5,
            "allow_rotation": False,
            "category": "BEVERAGE"
        }
    ]
    
    candidate_boxes = [
        {
            # Box A: height 25cm -> usable height with 10% dunnage = 22.5cm < 32cm
            # Even though length 40cm > 32cm, cannot lay flat!
            "box_id": "BOX-SHORT-FLAT",
            "name": "Short Flat Box",
            "length": 40.0,
            "width": 30.0,
            "height": 25.0,
            "max_weight": 10.0,
            "volume": 30000.0
        },
        {
            # Box B: height 40cm -> usable height = 36cm >= 32cm -> FITS upright!
            "box_id": "BOX-TALL-UPRIGHT",
            "name": "Tall Upright Box",
            "length": 25.0,
            "width": 25.0,
            "height": 40.0,
            "max_weight": 10.0,
            "volume": 25000.0
        }
    ]
    
    mock_db_client.fetch_many.side_effect = [
        bottle_item,
        candidate_boxes
    ]
    
    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-LIQUID-01")
    assert result.success is True
    recs = result.data["recommendations"]
    assert len(recs) == 1
    assert recs[0]["box_id"] == "BOX-TALL-UPRIGHT"


@pytest.mark.asyncio
async def test_dunnage_buffer_deduction(mock_db_client, test_config):
    """
    Test 10% dunnage buffer:
    Box length = 20.0cm -> usable length with 10% buffer is 18.0cm.
    An item with length = 19.0cm must NOT fit.
    """
    tight_item = [
        {
            "sku_code": "SKU-TIGHT-01",
            "quantity": 1,
            "length": 19.0,
            "width": 10.0,
            "height": 5.0,
            "weight": 1.0,
            "allow_rotation": True,
            "category": "GENERAL"
        }
    ]
    
    candidate_boxes = [
        {
            "box_id": "BOX-20CM",
            "name": "20cm Box",
            "length": 20.0,
            "width": 15.0,
            "height": 10.0,
            "max_weight": 5.0,
            "volume": 3000.0
        },
        {
            "box_id": "BOX-25CM",
            "name": "25cm Box",
            "length": 25.0,
            "width": 15.0,
            "height": 10.0,
            "max_weight": 5.0,
            "volume": 3750.0
        }
    ]
    
    mock_db_client.fetch_many.side_effect = [
        tight_item,
        candidate_boxes
    ]
    
    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-BUFFER-01")
    assert result.success is True
    recs = result.data["recommendations"]
    # BOX-20CM usable length is 18cm, so 19cm item is rejected
    assert len(recs) == 1
    assert recs[0]["box_id"] == "BOX-25CM"


@pytest.mark.asyncio
async def test_hazmat_segregation_food_conflict(mock_db_client, test_config):
    """
    Acceptance Criteria: Ngăn chặn việc đóng chung sản phẩm thuộc nhóm hazmat_class
    với thực phẩm hoặc đồ điện tử trong cùng một thùng carton.
    """
    mixed_order_items = [
        {
            "sku_code": "SKU-HAZMAT-ACID",
            "name": "Hydrochloric Acid Cleaner",
            "quantity": 1,
            "length": 10.0,
            "width": 10.0,
            "height": 15.0,
            "weight": 2.0,
            "hazmat_class": "CLASS_8_CORROSIVE",
            "category": "HAZMAT"
        },
        {
            "sku_code": "SKU-ORGANIC-MILK",
            "name": "Fresh Organic Milk",
            "quantity": 2,
            "length": 10.0,
            "width": 8.0,
            "height": 20.0,
            "weight": 2.0,
            "hazmat_class": None,
            "category": "FOOD"
        }
    ]
    
    mock_db_client.fetch_many.return_value = mixed_order_items
    
    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-HAZMAT-FOOD")
    assert result.success is False
    assert result.error_code == "HAZMAT_INCOMPATIBILITY"
    assert "Hazmat" in result.error
    assert result.data["hazmat_incompatible"] is True


@pytest.mark.asyncio
async def test_hazmat_segregation_electronics_conflict(mock_db_client, test_config):
    """
    Test hazmat mixed with electronics must be rejected.
    """
    mixed_items = [
        {
            "sku_code": "SKU-HAZMAT-SOLVENT",
            "name": "Industrial Solvent",
            "quantity": 1,
            "length": 12.0,
            "width": 12.0,
            "height": 18.0,
            "weight": 1.5,
            "hazmat_class": "CLASS_3_FLAMMABLE",
            "category": "HAZMAT"
        },
        {
            "sku_code": "SKU-PHONE-01",
            "name": "Smart Phone Pro",
            "quantity": 1,
            "length": 15.0,
            "width": 8.0,
            "height": 2.0,
            "weight": 0.3,
            "hazmat_class": None,
            "category": "ELECTRONICS"
        }
    ]
    
    mock_db_client.fetch_many.return_value = mixed_items
    
    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-HAZMAT-ELEC")
    assert result.success is False
    assert result.error_code == "HAZMAT_INCOMPATIBILITY"


@pytest.mark.asyncio
async def test_dimensional_weight_billable_optimization(mock_db_client, test_config):
    """
    Acceptance Criteria: Tính toán cước trọng lượng thể tích DIM Weight = (L*W*H)/5000
    và so sánh với Gross Weight để đề xuất hộp tối ưu chi phí cước.
    """
    item = [
        {
            "sku_code": "SKU-LIGHT-PLUSH",
            "quantity": 1,
            "length": 20.0,
            "width": 15.0,
            "height": 10.0,
            "weight": 0.5,  # Very light item (Gross weight = 0.5 kg)
            "allow_rotation": True,
            "category": "TOY"
        }
    ]
    
    candidate_boxes = [
        {
            # Box S: 25 x 20 x 15 -> DIM weight = 7500 / 5000 = 1.5 kg -> Billable weight = 1.5 kg
            "box_id": "BOX-S",
            "name": "Small Box (S)",
            "length": 25.0,
            "width": 20.0,
            "height": 15.0,
            "max_weight": 5.0,
            "volume": 7500.0
        },
        {
            # Box M: 40 x 30 x 25 -> DIM weight = 30000 / 5000 = 6.0 kg -> Billable weight = 6.0 kg
            "box_id": "BOX-M",
            "name": "Medium Box (M)",
            "length": 40.0,
            "width": 30.0,
            "height": 25.0,
            "max_weight": 15.0,
            "volume": 30000.0
        }
    ]
    
    mock_db_client.fetch_many.side_effect = [
        item,
        candidate_boxes
    ]
    
    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-DIM-01")
    assert result.success is True
    recs = result.data["recommendations"]
    assert len(recs) == 2
    
    box_s = next(r for r in recs if r["box_id"] == "BOX-S")
    assert box_s["dim_weight_kg"] == 1.5
    assert box_s["billable_weight_kg"] == 1.5
    
    box_m = next(r for r in recs if r["box_id"] == "BOX-M")
    assert box_m["dim_weight_kg"] == 6.0
    assert box_m["billable_weight_kg"] == 6.0
    
    # Box S must be chosen first because of lower billable shipping weight
    assert recs[0]["box_id"] == "BOX-S"


def test_base_support_gravity_constraint_unit():
    """
    Acceptance Criteria (TASK-062):
    1. If pz == 0: perfectly supported by the carton bottom (True).
    2. If pz > 0 and base support ratio >= 70%: True.
    3. If pz > 0 and base support ratio < 70%: False (floating / hanging item rejected).
    """
    item = {"sku_code": "SKU-TEST-01", "weight": 1.0}

    # 1. On bottom (pz = 0) -> always valid
    assert _has_sufficient_base_support(item, (0, 0, 0, 20, 20, 10), [], min_ratio=0.70) is True

    # 2. Supported by box below (100% support)
    placed_100 = [(0, 0, 0, 20, 20, 10, {"sku_code": "SKU-BASE", "is_fragile": False})]
    assert _has_sufficient_base_support(item, (0, 0, 10, 20, 20, 10), placed_100, min_ratio=0.70) is True

    # 3. Supported by box below (75% support >= 70%)
    # Base box: 20 x 15 -> area 300; candidate item: 20 x 20 -> area 400; ratio = 300/400 = 75%
    placed_75 = [(0, 0, 0, 20, 15, 10, {"sku_code": "SKU-BASE", "is_fragile": False})]
    assert _has_sufficient_base_support(item, (0, 0, 10, 20, 20, 10), placed_75, min_ratio=0.70) is True

    # 4. Under-supported by box below (50% support < 70%) -> REJECTED
    # Base box: 20 x 10 -> area 200; candidate item: 20 x 20 -> area 400; ratio = 50%
    placed_50 = [(0, 0, 0, 20, 10, 10, {"sku_code": "SKU-BASE", "is_fragile": False})]
    assert _has_sufficient_base_support(item, (0, 0, 10, 20, 20, 10), placed_50, min_ratio=0.70) is False

    # 5. Gap / floating in air (placed box top at z=8, item placed at z=10) -> REJECTED
    placed_gap = [(0, 0, 0, 20, 20, 8, {"sku_code": "SKU-BASE", "is_fragile": False})]
    assert _has_sufficient_base_support(item, (0, 0, 10, 20, 20, 10), placed_gap, min_ratio=0.70) is False


def test_fragile_constraint_heavy_item_rejected_unit():
    """
    Acceptance Criteria (TASK-062):
    Tuyệt đối không xếp kiện hàng có trọng lượng > 2.0kg đè lên kiện hàng có thuộc tính is_fragile=True.
    """
    fragile_base = [(0, 0, 0, 20, 20, 10, {"sku_code": "SKU-GLASS", "is_fragile": True})]
    non_fragile_base = [(0, 0, 0, 20, 20, 10, {"sku_code": "SKU-WOOD", "is_fragile": False})]

    # 1. Heavy item (weight = 2.5kg > 2.0kg) placed on fragile item -> REJECTED
    heavy_item = {"sku_code": "SKU-HEAVY", "weight": 2.5}
    assert _has_sufficient_base_support(heavy_item, (0, 0, 10, 20, 20, 10), fragile_base) is False

    # 2. Borderline heavy item (weight = 5.0kg) placed on fragile item -> REJECTED
    very_heavy_item = {"sku_code": "SKU-ANVIL", "weight": 5.0}
    assert _has_sufficient_base_support(very_heavy_item, (0, 0, 10, 20, 20, 10), fragile_base) is False

    # 3. Light item (weight = 1.2kg <= 2.0kg) placed on fragile item -> ALLOWED
    light_item = {"sku_code": "SKU-LIGHT", "weight": 1.2}
    assert _has_sufficient_base_support(light_item, (0, 0, 10, 20, 20, 10), fragile_base) is True

    # 4. Heavy item (weight = 15.0kg) placed on non-fragile item -> ALLOWED
    assert _has_sufficient_base_support(very_heavy_item, (0, 0, 10, 20, 20, 10), non_fragile_base) is True


@pytest.mark.asyncio
async def test_oversized_item_error_result(mock_db_client, test_config):
    """
    Acceptance Criteria (TASK-062 / MED-10):
    Nếu không có bất kỳ thùng carton nào chứa vừa sản phẩm:
    Trả về ToolResult(success=False, error_code="OVERSIZED_ITEM",
    error="Order contains oversized items exceeding all available carton dimensions. Palletizing / custom crate required.")
    """
    oversized_item = [
        {
            "sku_code": "SKU-GIANT-CRATE",
            "name": "Industrial Generator",
            "quantity": 1,
            "length": 250.0,  # Exceeds even XXL (140cm)
            "width": 180.0,
            "height": 120.0,
            "weight": 80.0,
            "allow_rotation": True,
            "category": "MACHINERY"
        }
    ]
    
    mock_db_client.fetch_many.side_effect = [
        oversized_item,
        []  # Fallback to default candidate boxes (max length 140cm)
    ]
    
    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-OVERSIZED-99")
    assert result.success is False
    assert result.error_code == "OVERSIZED_ITEM"
    assert "Order contains oversized items exceeding all available carton dimensions. Palletizing / custom crate required." in result.error
    assert result.data["order_id"] == "ORD-OVERSIZED-99"


@pytest.mark.asyncio
async def test_3d_bpp_packing_gravity_and_fragile_integration(mock_db_client, test_config):
    """
    Integration test: Order contains a fragile item and a heavy item in a vertical-stack-only box.
    Sturdy heavy item must be placed at the bottom, and fragile item on top.
    """
    order_items = [
        {
            "sku_code": "SKU-GLASSWARE",
            "name": "Crystal Vase",
            "quantity": 1,
            "length": 20.0,
            "width": 15.0,
            "height": 10.0,
            "weight": 1.0,
            "allow_rotation": False,
            "is_fragile": True,
            "category": "FRAGILE"
        },
        {
            "sku_code": "SKU-DUMBBELL",
            "name": "Cast Iron Dumbbell",
            "quantity": 1,
            "length": 20.0,
            "width": 15.0,
            "height": 10.0,
            "weight": 4.5,  # > 2.0kg
            "allow_rotation": False,
            "is_fragile": False,
            "category": "FITNESS"
        }
    ]
    
    # Candidate box: 25 x 20 x 25.
    # Usable dimensions with 10% dunnage: 22.5 x 18 x 22.5.
    # Floor can only fit ONE item (20 x 15), so items MUST stack vertically (height: 10 + 10 = 20 <= 22.5).
    candidate_boxes = [
        {
            "box_id": "BOX-STACK-VERTICAL",
            "name": "Vertical Stack Box",
            "length": 25.0,
            "width": 20.0,
            "height": 25.0,
            "max_weight": 20.0,
            "volume": 12500.0
        }
    ]
    
    mock_db_client.fetch_many.side_effect = [
        order_items,
        candidate_boxes
    ]
    
    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client
    
    result = await tool.execute(order_id="ORD-FRAGILE-STACK")
    assert result.success is True
    recs = result.data["recommendations"]
    assert len(recs) == 1
    assert recs[0]["box_id"] == "BOX-STACK-VERTICAL"

