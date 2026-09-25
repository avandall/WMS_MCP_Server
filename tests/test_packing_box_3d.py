"""Unit tests for 3D-BPP Geometric Packing & Hazmat Segregation (TASK-045 / ALG-01)"""

import pytest

from app.tools.orders.suggest_packing_box import (
    SuggestPackingBox,
    _has_sufficient_base_support,
    calculate_center_of_gravity,
    check_center_of_gravity,
    adjust_placement_for_center_of_gravity,
    partition_sioc_items,
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


# ==============================================================================
# TASK-067: Center of Gravity Optimization & Mass Distribution (DOM-02)
# ==============================================================================

def test_center_of_gravity_unit_functions():
    """
    Acceptance Criteria (TASK-067 / DOM-02):
    1. calculate_center_of_gravity: Computes weighted CoG (X_cg, Y_cg, Z_cg).
    2. check_center_of_gravity: Detects offset > 20% from geometric center.
    3. adjust_placement_for_center_of_gravity: Translates placed items towards center bottom
       to bring CoG within safe +-20% zone.
    """
    # Item: 20x20x20cm, 15kg placed at origin (0, 0, 0)
    placed_boxes = [(0.0, 0.0, 0.0, 20.0, 20.0, 20.0, {"weight": 15.0})]
    box_l, box_w, box_h = 60.0, 40.0, 35.0
    # Geometric center: X=30.0, Y=20.0, Z=17.5

    # 1. Calculate CoG
    cog = calculate_center_of_gravity(placed_boxes, box_l, box_w, box_h)
    assert cog == (10.0, 10.0, 10.0)

    # 2. Check CoG before adjustment (offset X = |10 - 30| = 20 / 60 = 33.3% > 20%)
    chk_before = check_center_of_gravity(placed_boxes, box_l, box_w, box_h, max_offset_ratio=0.20)
    assert chk_before["is_balanced"] is False
    assert chk_before["offset_x"] == 20.0
    assert chk_before["offset_ratio_x"] == pytest.approx(0.3333, 0.001)

    # 3. Adjust placement towards carton center
    adjusted = adjust_placement_for_center_of_gravity(placed_boxes, box_l, box_w, box_h)
    assert len(adjusted) == 1
    new_px, new_py, new_pz = adjusted[0][0], adjusted[0][1], adjusted[0][2]
    # To align CoG (10, 10) to (30, 20), shift is dx = +20, dy = +10
    assert new_px == 20.0
    assert new_py == 10.0
    assert new_pz == 0.0

    # 4. Check CoG after adjustment
    chk_after = check_center_of_gravity(adjusted, box_l, box_w, box_h, max_offset_ratio=0.20)
    assert chk_after["is_balanced"] is True
    assert chk_after["center_of_gravity"] == (30.0, 20.0, 10.0)
    assert chk_after["offset_x"] == 0.0
    assert chk_after["offset_y"] == 0.0
    assert chk_after["offset_ratio_x"] <= 0.20
    assert chk_after["offset_ratio_y"] <= 0.20


@pytest.mark.asyncio
async def test_center_of_gravity_heavy_item_centering(mock_db_client, test_config):
    """
    Acceptance Criteria (TASK-067 / DOM-02):
    Đơn hàng gồm 1 vật nặng 15kg (20x20x20) và 2 vật nhẹ 0.5kg (10x10x10):
    Trọng tâm thùng carton đóng gói phải nằm trong vùng an toàn +- 20%.
    """
    order_items = [
        {
            "sku_code": "SKU-CAST-IRON",
            "name": "Heavy Cast Iron Part",
            "quantity": 1,
            "length": 20.0,
            "width": 20.0,
            "height": 20.0,
            "weight": 15.0,
            "allow_rotation": True,
            "category": "HARDWARE"
        },
        {
            "sku_code": "SKU-FOAM-PADDING",
            "name": "Foam Spacer",
            "quantity": 2,
            "length": 10.0,
            "width": 10.0,
            "height": 10.0,
            "weight": 0.5,
            "allow_rotation": True,
            "category": "PACKING"
        }
    ]

    candidate_boxes = [
        {
            "box_id": "BOX-LARGE-L",
            "name": "Large Box (L)",
            "length": 60.0,
            "width": 40.0,
            "height": 35.0,
            "max_weight": 30.0,
            "volume": 84000.0
        }
    ]

    mock_db_client.fetch_many.side_effect = [
        order_items,
        candidate_boxes
    ]

    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client

    result = await tool.execute(order_id="ORD-HEAVY-PART-15KG")
    assert result.success is True
    recs = result.data["recommendations"]
    assert len(recs) == 1
    selected = recs[0]

    # Verify CoG metrics in recommendation
    assert selected["is_cog_balanced"] is True
    assert selected["cog_status"] == "BALANCED"
    assert selected["cog_offset_ratio_x"] <= 0.20
    assert selected["cog_offset_ratio_y"] <= 0.20


# ==============================================================================
# TASK-068: Automatic SIOC Master Carton Recognition (DOM-03)
# ==============================================================================

@pytest.mark.asyncio
async def test_sioc_master_carton_recognition(mock_db_client, test_config):
    """
    Acceptance Criteria (TASK-068 / DOM-03):
    Đơn hàng 50 lon (1 Case = 24 lon):
    -> 2 Thùng nguyên (48 lon): Xuất nguyên kiện SIOC (Dán nhãn vận chuyển trực tiếp)
    -> 2 Lon lẻ: Đưa vào 3D-BPP để đóng gói vào hộp carton nhỏ
    """
    order_items = [
        {
            "sku_code": "SKU-SODA-CAN",
            "name": "Sparkling Soda Can 330ml",
            "quantity": 50,
            "length": 6.0,
            "width": 6.0,
            "height": 12.0,
            "weight": 0.35,
            "case_size": 24,
            "allow_rotation": True,
            "category": "BEVERAGE"
        }
    ]

    candidate_boxes = [
        {
            "box_id": "BOX-S",
            "name": "Small Box (S)",
            "length": 25.0,
            "width": 20.0,
            "height": 15.0,
            "max_weight": 5.0,
            "volume": 7500.0
        }
    ]

    mock_db_client.fetch_many.side_effect = [
        order_items,
        candidate_boxes
    ]

    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client

    result = await tool.execute(order_id="ORD-SODA-50-CANS")
    assert result.success is True
    data = result.data

    # SIOC Master Carton packages check (50 // 24 = 2 cases)
    sioc_pkgs = data["sioc_packages"]
    assert len(sioc_pkgs) == 2
    for pkg in sioc_pkgs:
        assert pkg["is_sioc"] is True
        assert pkg["package_type"] == "SIOC"
        assert pkg["quantity_per_case"] == 24
        assert pkg["sku_code"] == "SKU-SODA-CAN"
        assert "Dán nhãn vận chuyển trực tiếp" in pkg["instructions"]

    # Loose items check (50 % 24 = 2 loose cans)
    loose = data["loose_items"]
    assert len(loose) == 1
    assert loose[0]["sku_code"] == "SKU-SODA-CAN"
    assert loose[0]["quantity"] == 2

    # 3D-BPP recommendation for the 2 loose cans
    recs = data["recommendations"]
    assert len(recs) >= 1
    assert recs[0]["box_id"] == "BOX-S"


@pytest.mark.asyncio
async def test_sioc_fully_master_carton_no_repack(mock_db_client, test_config):
    """
    Acceptance Criteria (TASK-068 / DOM-03):
    Đơn hàng đủ thùng nguyên (48 lon = 2 Case x 24):
    Không bị xé lẻ đóng hộp lại, không cần thùng carton phụ.
    """
    order_items = [
        {
            "sku_code": "SKU-BEER-CAN",
            "name": "Craft Beer Can 330ml",
            "quantity": 48,
            "length": 6.0,
            "width": 6.0,
            "height": 12.0,
            "weight": 0.35,
            "case_size": 24,
            "allow_rotation": True,
            "category": "BEVERAGE"
        }
    ]

    mock_db_client.fetch_many.side_effect = [
        order_items,
        []  # No candidate boxes needed because 100% SIOC
    ]

    tool = SuggestPackingBox(test_config)
    tool.db = mock_db_client

    result = await tool.execute(order_id="ORD-BEER-48-FULL")
    assert result.success is True
    data = result.data

    assert data["is_fully_sioc"] is True
    assert len(data["sioc_packages"]) == 2
    assert len(data["loose_items"]) == 0
    assert len(data["recommendations"]) == 0
    assert data["selected_recommendation"]["package_type"] == "SIOC"
    assert "Toàn bộ đơn hàng" in data["selected_recommendation"]["message"]


def test_sioc_partition_via_uom_conversion():
    """Test partition_sioc_items using product UOM conversion factors."""
    items = [
        {
            "sku_code": "SKU-COKE-UOM",
            "name": "Coca Cola 330ml",
            "quantity": 25,
            "length": 6.0,
            "width": 6.0,
            "height": 12.0,
            "weight": 0.35,
            "uoms": [
                {"uom_code": "CASE", "conversion_factor": 12.0, "to_uom_code": "EACH"}
            ]
        }
    ]

    sioc_pkgs, loose = partition_sioc_items(items)
    # 25 // 12 = 2 cases (24 units), 1 loose unit
    assert len(sioc_pkgs) == 2
    assert sioc_pkgs[0]["quantity_per_case"] == 12
    assert sioc_pkgs[1]["quantity_per_case"] == 12
    assert len(loose) == 1
    assert loose[0]["quantity"] == 1


# ==============================================================================
# TASK-078: SIOC Safety Limits (<= 32kg & <= 150cm) and Freight Pallet (DOM-03)
# ==============================================================================

def test_sioc_weight_limit_valid_15kg_vs_heavy_45kg():
    """
    Acceptance Criteria (TASK-078 / DOM-03):
    Kiểm thử phân tách SIOC với:
    - Kiện hàng 15kg (hợp lệ <= 32kg): Tạo nhãn SIOC bưu kiện thông thường (shipping_method = 'PARCEL', is_sioc = True).
    - Kiện hàng 45kg (quá tải > 32kg): Bắt buộc yêu cầu pallet (shipping_method = 'FREIGHT_PALLET', requires_freight_pallet = True).
    """
    items = [
        # Item 1: 15kg case (10 units x 1.5kg) -> Standard SIOC parcel
        {
            "sku_code": "SKU-LIGHT-CASE",
            "name": "Standard Light Item Case",
            "quantity": 10,
            "case_size": 10,
            "weight": 1.5,
            "length": 30.0,
            "width": 20.0,
            "height": 20.0,
        },
        # Item 2: 45kg case (10 units x 4.5kg) -> Heavy item requiring pallet
        {
            "sku_code": "SKU-HEAVY-DUMBBELL",
            "name": "Heavy Iron Dumbbell Case",
            "quantity": 10,
            "case_size": 10,
            "weight": 4.5,
            "length": 40.0,
            "width": 30.0,
            "height": 25.0,
        },
    ]

    packages, loose = partition_sioc_items(items)

    assert len(packages) == 2
    assert len(loose) == 0

    # Package 1: 15kg valid SIOC
    pkg_15kg = next(p for p in packages if p["sku_code"] == "SKU-LIGHT-CASE")
    assert pkg_15kg["gross_weight_kg"] == 15.0
    assert pkg_15kg["is_sioc"] is True
    assert pkg_15kg["package_type"] == "SIOC"
    assert pkg_15kg["shipping_method"] == "PARCEL"
    assert pkg_15kg["requires_freight_pallet"] is False
    assert pkg_15kg["shipping_label"].startswith("SHIP-SIOC")

    # Package 2: 45kg heavy case requiring freight pallet
    pkg_45kg = next(p for p in packages if p["sku_code"] == "SKU-HEAVY-DUMBBELL")
    assert pkg_45kg["gross_weight_kg"] == 45.0
    assert pkg_45kg["is_sioc"] is False
    assert pkg_45kg["package_type"] == "FREIGHT_PALLET"
    assert pkg_45kg["shipping_method"] == "FREIGHT_PALLET"
    assert pkg_45kg["requires_freight_pallet"] is True
    assert pkg_45kg["shipping_label"].startswith("FREIGHT-PALLET")
    assert "FREIGHT_PALLET" in pkg_45kg["instructions"]


def test_sioc_weight_limit_oversized_dimension():
    """
    Acceptance Criteria (TASK-078 / DOM-03):
    Kiện hàng kích thước vượt quá 150cm bị từ chối SIOC bưu kiện thông thường và yêu cầu pallet.
    """
    items = [
        {
            "sku_code": "SKU-OVERSIZED-PIPE",
            "name": "Industrial Long Pipe",
            "quantity": 5,
            "case_size": 5,
            "weight": 2.0,  # 5 * 2.0 = 10.0kg (under 32kg)
            "length": 160.0,  # 160cm > 150cm (oversized)
            "width": 20.0,
            "height": 20.0,
        }
    ]

    packages, loose = partition_sioc_items(items)
    assert len(packages) == 1
    pkg = packages[0]
    assert pkg["gross_weight_kg"] == 10.0
    assert pkg["max_dimension_cm"] == 160.0
    assert pkg["requires_freight_pallet"] is True
    assert pkg["shipping_method"] == "FREIGHT_PALLET"
    assert pkg["package_type"] == "FREIGHT_PALLET"



