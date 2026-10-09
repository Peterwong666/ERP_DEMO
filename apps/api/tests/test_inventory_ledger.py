from datetime import datetime
from decimal import Decimal

import pytest
from app.models import Inventory, InventoryTransaction, Product, Supplier
from app.models.enums import (
    ProductCategory,
    ProductStatus,
    StockType,
    SupplierStatus,
    TxnType,
)
from app.services.inventory_ledger import (
    LedgerEntry,
    LedgerError,
    find_reconciliation_mismatches,
    post_transaction,
    rebuild_inventory,
)
from sqlalchemy.orm import Session


def _make_product(db: Session, sku: str = "EC-0001") -> Product:
    supplier = Supplier(
        code=f"SUP-{sku}",
        name="测试供应商",
        contact_person="联系人",
        email="a@b.com",
        phone="123",
        country="中国",
        lead_time_days=7,
        status=SupplierStatus.active,
    )
    db.add(supplier)
    db.flush()
    product = Product(
        sku_code=sku,
        name="测试产品",
        category=ProductCategory.electronics,
        status=ProductStatus.on_sale,
        unit="件",
        standard_cost=Decimal("10.00"),
        weight_g=100,
        safety_stock=10,
        default_supplier_id=supplier.supplier_id,
    )
    db.add(product)
    db.flush()
    return product


def _entry(product: Product, change_qty: int, stock_type: StockType) -> LedgerEntry:
    return LedgerEntry(
        product_id=product.product_id,
        change_qty=change_qty,
        stock_type=stock_type,
        txn_type=TxnType.recv_inbound,
        ref_doc_type="PO",
        ref_doc_no="PO-TEST-01",
        operator="仓管员",
    )


def test_post_transaction_creates_inventory_row_and_writes_txn(db: Session) -> None:
    product = _make_product(db)

    txn = post_transaction(db, _entry(product, 100, StockType.pending))

    inventory = db.query(Inventory).filter_by(product_id=product.product_id).one()
    assert inventory.qty_pending == 100
    assert inventory.qty_available == 0
    assert txn.change_qty == 100
    assert txn.stock_type == StockType.pending
    assert txn.ref_doc_no == "PO-TEST-01"
    assert txn.operator == "仓管员"
    assert isinstance(txn.created_at, datetime)


def test_post_transaction_accumulates_balances(db: Session) -> None:
    product = _make_product(db)

    post_transaction(db, _entry(product, 100, StockType.pending))
    post_transaction(db, _entry(product, 50, StockType.pending))

    inventory = db.query(Inventory).filter_by(product_id=product.product_id).one()
    assert inventory.qty_pending == 150
    assert db.query(InventoryTransaction).count() == 2


def test_post_transaction_rejects_negative_balance(db: Session) -> None:
    product = _make_product(db)
    post_transaction(db, _entry(product, 30, StockType.pending))

    with pytest.raises(LedgerError):
        post_transaction(db, _entry(product, -40, StockType.pending))

    inventory = db.query(Inventory).filter_by(product_id=product.product_id).one()
    assert inventory.qty_pending == 30


def test_post_transaction_rejects_zero_change(db: Session) -> None:
    product = _make_product(db)

    with pytest.raises(LedgerError):
        post_transaction(db, _entry(product, 0, StockType.pending))


def test_rebuild_inventory_recomputes_balances_from_transactions(db: Session) -> None:
    product = _make_product(db)
    post_transaction(db, _entry(product, 100, StockType.pending))
    post_transaction(db, _entry(product, -40, StockType.pending))
    # 模拟物化余额被破坏
    inventory = db.query(Inventory).filter_by(product_id=product.product_id).one()
    inventory.qty_pending = 999

    row_count = rebuild_inventory(db)

    db.expire_all()
    rebuilt = db.query(Inventory).filter_by(product_id=product.product_id).one()
    assert rebuilt.qty_pending == 60
    assert row_count == 1


def test_find_reconciliation_mismatches_detects_drift(db: Session) -> None:
    product = _make_product(db)
    post_transaction(db, _entry(product, 100, StockType.pending))

    inventory = db.query(Inventory).filter_by(product_id=product.product_id).one()
    inventory.qty_pending = 80

    mismatches = find_reconciliation_mismatches(db)

    assert len(mismatches) == 1
    mismatch = mismatches[0]
    assert mismatch.product_id == product.product_id
    assert mismatch.stock_type == StockType.pending
    assert mismatch.book_qty == 80
    assert mismatch.ledger_qty == 100


def test_find_reconciliation_mismatches_empty_when_consistent(db: Session) -> None:
    product = _make_product(db)
    post_transaction(db, _entry(product, 100, StockType.pending))

    assert find_reconciliation_mismatches(db) == []


def test_find_reconciliation_mismatches_reports_missing_inventory_row(
    db: Session,
) -> None:
    product = _make_product(db)
    post_transaction(db, _entry(product, 100, StockType.pending))
    # 物化行整体丢失（流水仍在）
    db.query(Inventory).delete()

    mismatches = find_reconciliation_mismatches(db)

    assert len(mismatches) == 1
    mismatch = mismatches[0]
    assert mismatch.product_id == product.product_id
    assert mismatch.stock_type == StockType.pending
    assert mismatch.book_qty == 0
    assert mismatch.ledger_qty == 100


def test_post_transaction_cross_stock_type_does_not_lend_balance(
    db: Session,
) -> None:
    product = _make_product(db)
    post_transaction(db, _entry(product, 100, StockType.pending))

    with pytest.raises(LedgerError):
        post_transaction(db, _entry(product, -10, StockType.available))

    inventory = db.query(Inventory).filter_by(product_id=product.product_id).one()
    assert inventory.qty_pending == 100
    assert inventory.qty_available == 0


def test_post_transaction_rejects_negative_first_post(db: Session) -> None:
    product = _make_product(db)

    with pytest.raises(LedgerError):
        post_transaction(db, _entry(product, -5, StockType.available))

    assert db.query(Inventory).count() == 0


def test_rebuild_inventory_covers_multiple_products(db: Session) -> None:
    product_a = _make_product(db, sku="EC-0001")
    product_b = _make_product(db, sku="EC-0002")
    post_transaction(db, _entry(product_a, 100, StockType.pending))
    post_transaction(db, _entry(product_b, 70, StockType.pending))

    row_count = rebuild_inventory(db)

    assert row_count == 2
    balances = {
        inventory.product_id: inventory.qty_pending
        for inventory in db.query(Inventory).all()
    }
    assert balances == {product_a.product_id: 100, product_b.product_id: 70}


def test_rebuild_inventory_refreshes_stale_loaded_instance(db: Session) -> None:
    product = _make_product(db)
    post_transaction(db, _entry(product, 100, StockType.pending))
    stale_ref = db.query(Inventory).filter_by(product_id=product.product_id).one()
    post_transaction(db, _entry(product, -40, StockType.pending))

    rebuild_inventory(db)

    assert stale_ref.qty_pending == 60
