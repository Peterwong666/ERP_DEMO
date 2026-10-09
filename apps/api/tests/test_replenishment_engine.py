"""Module 2D：补货规则引擎服务与 HTTP。

验收：种子数据生成 8 行建议、紧急/建议/正常三态齐全；
看板 suggestion_count 与引擎行数同源；6 个低库存 SKU 全部在列。
"""

from collections import Counter
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    DailySales,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
)
from app.models.enums import (
    POStatus,
    ProductCategory,
    ProductStatus,
    StockType,
    SupplierStatus,
    TxnType,
    Urgency,
)
from app.seeds.builder import seed_all
from app.services import inventory_ledger
from app.services.metrics_service import compute_metrics
from app.services.replenishment_service import (
    generate_suggestions,
    list_suggestions,
)
from app.services.settings_service import update_values
from app.services.stock_analytics import find_low_stock

ANCHOR_D = date(2026, 10, 9)


def _supplier(db: Session, code: str) -> Supplier:
    supplier = Supplier(
        code=code,
        name="测试供应商",
        contact_person="x",
        email="x@example.com",
        phone="1",
        country="CN",
        lead_time_days=7,
        status=SupplierStatus.active,
    )
    db.add(supplier)
    db.flush()
    return supplier


def _product(db: Session, sku: str, safety: int = 10) -> Product:
    supplier = _supplier(db, f"S-{sku}")
    product = Product(
        sku_code=sku,
        name=sku,
        category=ProductCategory.electronics,
        status=ProductStatus.on_sale,
        unit="件",
        standard_cost=Decimal("1.00"),
        weight_g=1,
        safety_stock=safety,
        default_supplier_id=supplier.supplier_id,
    )
    db.add(product)
    db.flush()
    return product


def _stock(db: Session, product: Product, qty: int) -> None:
    inventory_ledger.post_transaction(
        db,
        inventory_ledger.LedgerEntry(
            product_id=product.product_id,
            change_qty=qty,
            stock_type=StockType.available,
            txn_type=TxnType.manual_adjust,
            ref_doc_type="opening",
            ref_doc_no=f"OPEN-{product.sku_code}",
            operator="tester",
        ),
    )


def _sales(db: Session, product: Product, daily_qty: int) -> None:
    for offset in range(1, 8):
        db.add(
            DailySales(
                product_id=product.product_id,
                date=ANCHOR_D.replace(day=9 - offset),
                qty_sold=daily_qty,
            )
        )
    db.flush()


def _in_transit_po(
    db: Session, product: Product, ordered: int, received: int
) -> None:
    supplier = _supplier(db, f"SUP-{product.sku_code}")
    po = PurchaseOrder(
        po_no=f"PO-{product.sku_code}",
        supplier_id=supplier.supplier_id,
        status=POStatus.partial_received,
        total_amount=Decimal("0"),
        order_date=ANCHOR_D,
        created_by="tester",
    )
    db.add(po)
    db.flush()
    db.add(
        PurchaseOrderItem(
            po_id=po.po_id,
            product_id=product.product_id,
            qty_ordered=ordered,
            qty_received=received,
            unit_price=Decimal("1"),
        )
    )
    db.flush()


# ---------- 单 SKU 计算 ----------


def test_forecast_cover_and_urgency(db: Session) -> None:
    product = _product(db, "R-1")
    _stock(db, product, 100)
    _sales(db, product, 10)

    rows = generate_suggestions(db)

    assert len(rows) == 1
    row = rows[0]
    assert row.forecast_7d == 70
    assert row.days_cover == 10
    assert row.current_stock == 100
    assert row.qty_in_transit == 0
    assert row.urgency is Urgency.emergency


def test_zero_sales_sku_not_generated(db: Session) -> None:
    product = _product(db, "R-2")
    _stock(db, product, 5)

    assert generate_suggestions(db) == []


def test_urgency_suggest_normal_and_not_candidate(db: Session) -> None:
    suggest_p = _product(db, "R-3A")
    _stock(db, suggest_p, 150)
    _sales(db, suggest_p, 10)  # cover 15

    normal_p = _product(db, "R-3B")
    _stock(db, normal_p, 250)
    _sales(db, normal_p, 10)  # cover 25，30 天目标缺口 50

    full_p = _product(db, "R-3C")
    _stock(db, full_p, 300)
    _sales(db, full_p, 10)  # cover 30，无缺口

    rows = generate_suggestions(db)
    urgency_by_sku = {row.product_id: row.urgency for row in rows}

    assert urgency_by_sku[suggest_p.product_id] is Urgency.suggest
    assert urgency_by_sku[normal_p.product_id] is Urgency.normal
    assert full_p.product_id not in urgency_by_sku


def test_urgency_boundaries_are_inclusive(db: Session) -> None:
    at_emergency = _product(db, "R-4A")
    _stock(db, at_emergency, 100)  # cover 10
    _sales(db, at_emergency, 10)

    at_suggest = _product(db, "R-4B")
    _stock(db, at_suggest, 210)  # cover 21
    _sales(db, at_suggest, 10)

    rows = generate_suggestions(db)
    urgency_by_sku = {row.product_id: row.urgency for row in rows}

    assert urgency_by_sku[at_emergency.product_id] is Urgency.emergency
    assert urgency_by_sku[at_suggest.product_id] is Urgency.suggest


def test_emergency_threshold_setting_changes_urgency(db: Session) -> None:
    product = _product(db, "R-5")
    _stock(db, product, 100)
    _sales(db, product, 10)

    assert generate_suggestions(db)[0].urgency is Urgency.emergency

    update_values(db, {"urgency_emergency_days": "8"})

    assert generate_suggestions(db)[0].urgency is Urgency.suggest


def test_suggest_threshold_setting_changes_urgency(db: Session) -> None:
    product = _product(db, "R-6")
    _stock(db, product, 200)  # cover 20
    _sales(db, product, 10)

    assert generate_suggestions(db)[0].urgency is Urgency.suggest

    update_values(db, {"urgency_suggestion_days": "15"})
    # 30 天目标仍有缺口 → 候选保留，紧急度降为正常
    row = generate_suggestions(db)[0]
    assert row.urgency is Urgency.normal
    assert row.suggested_qty == 100

    update_values(db, {"urgency_suggestion_days": "30"})
    assert generate_suggestions(db)[0].urgency is Urgency.suggest


def test_in_transit_reduces_suggested_qty(db: Session) -> None:
    product = _product(db, "R-7")
    _stock(db, product, 50)
    _sales(db, product, 10)
    _in_transit_po(db, product, ordered=100, received=0)

    row = generate_suggestions(db)[0]

    assert row.qty_in_transit == 100
    assert row.suggested_qty == 150


def test_suggested_qty_zero_when_transit_covers(db: Session) -> None:
    product = _product(db, "R-8")
    _stock(db, product, 150)
    _sales(db, product, 10)
    _in_transit_po(db, product, ordered=200, received=0)

    assert generate_suggestions(db)[0].suggested_qty == 0


def test_generate_twice_refreshes_without_duplicates(db: Session) -> None:
    product = _product(db, "R-9")
    _stock(db, product, 100)
    _sales(db, product, 10)

    first = generate_suggestions(db)
    second = generate_suggestions(db)

    assert len(first) == len(second) == 1
    assert first[0].product_id == second[0].product_id


def test_list_suggestions_empty_before_generation(db: Session) -> None:
    assert list_suggestions(db) == []


# ---------- 种子数据整体验收 ----------


def test_seeded_engine_8_rows_with_three_urgencies(db: Session) -> None:
    seed_all(db)

    rows = generate_suggestions(db)

    assert len(rows) == 8
    assert Counter(row.urgency for row in rows) == Counter(
        {Urgency.emergency: 3, Urgency.suggest: 4, Urgency.normal: 1}
    )
    assert [row.days_cover for row in rows] == [6, 8, 10, 11, 12, 17, 21, 22]


def test_seeded_six_low_stock_skus_all_in_suggestions(db: Session) -> None:
    seed_all(db)

    low_ids = {product.product_id for product, _, _ in find_low_stock(db, ANCHOR_D)}
    suggestion_ids = {row.product_id for row in generate_suggestions(db)}

    assert len(low_ids) == 6
    assert low_ids <= suggestion_ids


def test_dashboard_counts_match_engine_rows(db: Session) -> None:
    seed_all(db)

    metrics = compute_metrics(db, ANCHOR_D)
    rows = generate_suggestions(db)

    assert metrics.suggestion_count == len(rows) == 8
    assert metrics.low_stock_count == 6


# ---------- HTTP ----------


def test_http_generate_and_list(client, db: Session) -> None:
    seed_all(db)

    assert client.get("/api/replenishment").json() == []

    generated = client.post("/api/replenishment/generate")
    assert generated.status_code == 200
    body = generated.json()
    assert len(body) == 8
    assert {row["urgency"] for row in body} == {"emergency", "suggest", "normal"}

    listed = client.get("/api/replenishment")
    assert len(listed.json()) == 8


def test_http_regenerate_keeps_8_rows(client, db: Session) -> None:
    seed_all(db)

    client.post("/api/replenishment/generate")
    client.post("/api/replenishment/generate")

    assert len(client.get("/api/replenishment").json()) == 8
