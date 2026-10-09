"""Module 2C：库存台账服务与 HTTP（余额列表、流水过滤、手工调整、对账、低库存）。"""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models import DailySales, Inventory, Product, Supplier
from app.models.enums import (
    ProductCategory,
    ProductStatus,
    StockType,
    SupplierStatus,
    TxnType,
)
from app.services import inventory_ledger
from app.services.inventory_service import (
    InventoryValidationError,
    list_balances,
    manual_adjust,
    query_transactions,
)
from app.services.settings_service import update_values
from app.services.stock_analytics import find_low_stock

ANCHOR = datetime(2026, 10, 9)


def _product(db: Session, sku: str = "T-001", safety_stock: int = 10) -> Product:
    supplier = Supplier(
        code=f"S-{sku}",
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
    product = Product(
        sku_code=sku,
        name=sku,
        category=ProductCategory.electronics,
        status=ProductStatus.on_sale,
        unit="件",
        standard_cost=Decimal("1.00"),
        weight_g=1,
        safety_stock=safety_stock,
        default_supplier_id=supplier.supplier_id,
    )
    db.add(product)
    db.flush()
    return product


def _post(
    db: Session,
    product: Product,
    qty: int,
    *,
    stock_type: StockType = StockType.available,
    txn_type: TxnType = TxnType.manual_adjust,
    ref_no: str = "DOC-1",
    when: datetime = ANCHOR,
    reason: str | None = None,
):
    return inventory_ledger.post_transaction(
        db,
        inventory_ledger.LedgerEntry(
            product_id=product.product_id,
            change_qty=qty,
            stock_type=stock_type,
            txn_type=txn_type,
            ref_doc_type="manual",
            ref_doc_no=ref_no,
            operator="tester",
            reason=reason,
            created_at=when,
        ),
    )


# ---------- 余额列表 ----------


def test_list_balances_returns_qtys_and_product_fields(db: Session) -> None:
    product = _product(db, "LIST-1")
    _post(db, product, 50)
    _product(db, "LIST-2")  # 无库存行

    balances = list_balances(db)

    assert len(balances) == 1
    row = balances[0]
    assert row.product_id == product.product_id
    assert row.sku_code == "LIST-1"
    assert row.name == "LIST-1"
    assert row.qty_available == 50
    assert row.qty_pending == 0
    assert row.qty_defective == 0


# ---------- 流水过滤 ----------


def test_query_transactions_filters_by_product(db: Session) -> None:
    product1 = _product(db, "TXN-1")
    product2 = _product(db, "TXN-2")
    _post(db, product1, 10, ref_no="D-1")
    _post(db, product2, 20, ref_no="D-2")

    rows = query_transactions(db, product_id=product1.product_id)

    assert [row.product_id for row in rows] == [product1.product_id]


def test_query_transactions_filters_by_ref_doc_no(db: Session) -> None:
    product = _product(db, "TXN-3")
    _post(db, product, 10, ref_no="PO-2026-1")
    _post(db, product, 20, ref_no="PO-2026-2")

    rows = query_transactions(db, ref_doc_no="PO-2026-2")

    assert [row.ref_doc_no for row in rows] == ["PO-2026-2"]


def test_query_transactions_filters_by_txn_type(db: Session) -> None:
    product = _product(db, "TXN-4")
    _post(db, product, 10, txn_type=TxnType.manual_adjust, ref_no="M-1")
    _post(db, product, -5, txn_type=TxnType.adjust_outbound, ref_no="O-1")

    rows = query_transactions(db, txn_type=TxnType.adjust_outbound)

    assert [row.txn_type for row in rows] == [TxnType.adjust_outbound]


def test_query_transactions_filters_by_stock_type(db: Session) -> None:
    product = _product(db, "TXN-5")
    _post(db, product, 10, stock_type=StockType.available, ref_no="A-1")
    _post(db, product, 10, stock_type=StockType.pending, ref_no="P-1")

    rows = query_transactions(db, stock_type=StockType.pending)

    assert [row.stock_type for row in rows] == [StockType.pending]


def test_query_transactions_filters_by_date_range_inclusive(db: Session) -> None:
    product = _product(db, "TXN-6")
    _post(db, product, 1, ref_no="D-A", when=datetime(2026, 10, 1))
    _post(db, product, 2, ref_no="D-B", when=datetime(2026, 10, 5))
    _post(db, product, 3, ref_no="D-C", when=datetime(2026, 10, 9))

    rows = query_transactions(db, date_from="2026-10-02", date_to="2026-10-05")

    assert [row.ref_doc_no for row in rows] == ["D-B"]


def test_query_transactions_orders_newest_first(db: Session) -> None:
    product = _product(db, "TXN-7")
    _post(db, product, 1, ref_no="OLD", when=datetime(2026, 10, 1))
    _post(db, product, 1, ref_no="NEW", when=datetime(2026, 10, 9))

    rows = query_transactions(db)

    assert [row.ref_doc_no for row in rows] == ["NEW", "OLD"]


# ---------- 手工调整 ----------


def test_manual_adjust_positive_writes_signed_txn(db: Session) -> None:
    product = _product(db, "ADJ-1")

    txn = manual_adjust(db, product.product_id, 5, "盘盈入库")

    assert txn.txn_type is TxnType.manual_adjust
    assert txn.change_qty == 5
    assert txn.reason == "盘盈入库"
    assert list_balances(db)[0].qty_available == 5


def test_manual_adjust_negative_reduces_balance(db: Session) -> None:
    product = _product(db, "ADJ-2")
    _post(db, product, 10)

    txn = manual_adjust(db, product.product_id, -4, "盘亏出库")

    assert txn.change_qty == -4
    assert list_balances(db)[0].qty_available == 6


def test_manual_adjust_over_balance_raises_ledger_error(db: Session) -> None:
    product = _product(db, "ADJ-3")
    _post(db, product, 3)

    with pytest.raises(inventory_ledger.LedgerError):
        manual_adjust(db, product.product_id, -5, "盘亏")

    assert list_balances(db)[0].qty_available == 3


def test_manual_adjust_zero_qty_rejected(db: Session) -> None:
    product = _product(db, "ADJ-4")

    with pytest.raises(InventoryValidationError):
        manual_adjust(db, product.product_id, 0, "无效调整")


def test_manual_adjust_blank_reason_rejected(db: Session) -> None:
    product = _product(db, "ADJ-5")

    with pytest.raises(InventoryValidationError):
        manual_adjust(db, product.product_id, 1, "   ")


def test_manual_adjust_unknown_product_raises_lookup_error(db: Session) -> None:
    with pytest.raises(LookupError):
        manual_adjust(db, 999, 1, "原因")


def test_manual_adjust_no_restarts_sequence_each_day(db: Session) -> None:
    product = _product(db, "ADJ-6")
    _post(
        db,
        product,
        1,
        ref_no="ADJ-20261008-001",
        when=datetime(2026, 10, 8, 10, 0),
    )

    txn = manual_adjust(
        db, product.product_id, 1, "次日盘盈", now=datetime(2026, 10, 9, 9, 0)
    )

    assert txn.ref_doc_no == "ADJ-20261009-001"


# ---------- 低库存规则 ----------


def _last7_sales(db: Session, product: Product, qty: int) -> None:
    for offset in range(1, 8):
        db.add(
            DailySales(
                product_id=product.product_id,
                date=ANCHOR.date().replace(day=9 - offset),
                qty_sold=qty,
            )
        )
    db.flush()


def test_low_stock_when_available_not_above_safety(db: Session) -> None:
    product = _product(db, "LOW-1", safety_stock=100)
    _post(db, product, 100)  # available == safety，且无销量

    low = find_low_stock(db, ANCHOR.date())

    assert [row[0].product_id for row in low] == [product.product_id]


def test_low_stock_not_flagged_when_cover_at_threshold(db: Session) -> None:
    product = _product(db, "LOW-2", safety_stock=50)
    _post(db, product, 140)
    _last7_sales(db, product, 10)  # avg 10，cover 14

    assert find_low_stock(db, ANCHOR.date()) == []


def test_low_stock_flagged_when_cover_below_threshold(db: Session) -> None:
    product = _product(db, "LOW-3", safety_stock=50)
    _post(db, product, 100)
    _last7_sales(db, product, 10)  # cover 10 < 14

    low = find_low_stock(db, ANCHOR.date())

    assert len(low) == 1


def test_low_stock_setting_change_reflags_skus(db: Session) -> None:
    product = _product(db, "LOW-4", safety_stock=50)
    _post(db, product, 140)
    _last7_sales(db, product, 10)  # cover 14

    assert find_low_stock(db, ANCHOR.date()) == []

    update_values(db, {"low_stock_days_threshold": "21"})

    assert len(find_low_stock(db, ANCHOR.date())) == 1


# ---------- HTTP ----------


def test_http_full_adjust_and_query(client, db: Session) -> None:
    product = _product(db, "HTTP-1")

    created = client.post(
        "/api/inventory/adjust",
        json={"product_id": product.product_id, "change_qty": 7, "reason": "盘盈"},
    )
    assert created.status_code == 200
    assert created.json()["change_qty"] == 7

    balances = client.get("/api/inventory")
    assert balances.status_code == 200
    assert balances.json()[0]["qty_available"] == 7

    filtered = client.get(
        "/api/inventory/transactions", params={"ref_doc_no": "ADJ-"}
    )
    assert filtered.status_code == 200
    assert all(row["ref_doc_no"].startswith("ADJ-") for row in filtered.json())


def test_http_adjust_validation_errors(client, db: Session) -> None:
    product = _product(db, "HTTP-2")

    blank_reason = client.post(
        "/api/inventory/adjust",
        json={"product_id": product.product_id, "change_qty": 1, "reason": ""},
    )
    assert blank_reason.status_code == 400

    zero_qty = client.post(
        "/api/inventory/adjust",
        json={"product_id": product.product_id, "change_qty": 0, "reason": "x"},
    )
    assert zero_qty.status_code == 400

    unknown = client.post(
        "/api/inventory/adjust",
        json={"product_id": 999, "change_qty": 1, "reason": "x"},
    )
    assert unknown.status_code == 404


def test_http_adjust_insufficient_balance_returns_409(client, db: Session) -> None:
    product = _product(db, "HTTP-3")

    response = client.post(
        "/api/inventory/adjust",
        json={"product_id": product.product_id, "change_qty": -1, "reason": "盘亏"},
    )

    assert response.status_code == 409


def test_http_reconciliation_reports_corruption(client, db: Session) -> None:
    product = _product(db, "HTTP-4")
    _post(db, product, 10)

    assert client.get("/api/inventory/reconciliation").json() == []

    # 直接污染物化余额模拟账实漂移
    db.query(Inventory).filter_by(product_id=product.product_id).update(
        {"qty_available": 15}
    )
    db.commit()

    mismatches = client.get("/api/inventory/reconciliation").json()
    assert len(mismatches) == 1
    assert mismatches[0]["book_qty"] == 15
    assert mismatches[0]["ledger_qty"] == 10


def test_http_low_stock_listing(client, db: Session) -> None:
    product = _product(db, "HTTP-5", safety_stock=100)
    _post(db, product, 50)

    rows = client.get("/api/inventory/low-stock")

    assert rows.status_code == 200
    assert rows.json()[0]["sku_code"] == "HTTP-5"
