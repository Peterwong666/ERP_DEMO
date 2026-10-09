from decimal import Decimal

import pytest
from app.models import Product, Supplier
from app.models.enums import (
    POStatus,
    ProductCategory,
    ProductStatus,
    SupplierStatus,
)
from app.schemas.products import POCreate, POLineIn, ProductCreate, ProductUpdate
from app.services.po_service import POError, cancel_order, create_draft, place_order
from app.services.product_service import (
    change_status,
    create_product,
    list_products,
    update_product,
)
from sqlalchemy.orm import Session


def _supplier(db: Session, code: str = "SUP-001") -> Supplier:
    supplier = Supplier(
        code=code,
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
    return supplier


def _product_create(supplier_id: int, sku: str = "EC-0001") -> ProductCreate:
    return ProductCreate(
        sku_code=sku,
        name="测试产品",
        category=ProductCategory.electronics,
        standard_cost=Decimal("10.00"),
        weight_g=100,
        safety_stock=10,
        default_supplier_id=supplier_id,
    )


# ---------- 产品 ----------

def test_create_product_persists_and_defaults_on_sale(db: Session) -> None:
    supplier = _supplier(db)

    product = create_product(db, _product_create(supplier.supplier_id))

    assert product.product_id is not None
    assert product.status == ProductStatus.on_sale
    assert product.unit == "件"


def test_list_products_filters_by_category(db: Session) -> None:
    supplier = _supplier(db)
    electronics = _product_create(supplier.supplier_id, sku="EC-0001")
    electronics.category = ProductCategory.electronics
    bags = _product_create(supplier.supplier_id, sku="BG-0001")
    bags.category = ProductCategory.bags
    create_product(db, electronics)
    create_product(db, bags)

    result = list_products(db, category=ProductCategory.bags)

    assert [product.sku_code for product in result] == ["BG-0001"]


def test_update_product_changes_fields(db: Session) -> None:
    supplier = _supplier(db)
    product = create_product(db, _product_create(supplier.supplier_id))

    updated = update_product(
        db, product.product_id, ProductUpdate(name="新名称", safety_stock=25)
    )

    assert updated.name == "新名称"
    assert updated.safety_stock == 25
    assert updated.sku_code == "EC-0001"


def test_change_status_toggles_sale_state(db: Session) -> None:
    supplier = _supplier(db)
    product = create_product(db, _product_create(supplier.supplier_id))

    discontinued = change_status(db, product.product_id, ProductStatus.discontinued)
    assert discontinued.status == ProductStatus.discontinued

    on_sale = change_status(db, product.product_id, ProductStatus.on_sale)
    assert on_sale.status == ProductStatus.on_sale


def test_change_status_unknown_product_raises(db: Session) -> None:
    with pytest.raises(LookupError):
        change_status(db, 999, ProductStatus.on_sale)


# ---------- PO ----------

def _po_create(supplier_id: int, product: Product) -> POCreate:
    return POCreate(
        supplier_id=supplier_id,
        items=[
            POLineIn(
                product_id=product.product_id,
                qty_ordered=100,
                unit_price=Decimal("10.00"),
            )
        ],
    )


def test_create_draft_persists_items_and_total(db: Session) -> None:
    supplier = _supplier(db)
    product = create_product(db, _product_create(supplier.supplier_id))

    po = create_draft(db, _po_create(supplier.supplier_id, product))

    assert po.status == POStatus.draft
    assert po.po_no.startswith("PO-")
    assert len(po.items) == 1
    assert po.total_amount == Decimal("1000.00")


def test_create_draft_rejects_empty_lines(db: Session) -> None:
    supplier = _supplier(db)
    with pytest.raises(POError):
        create_draft(db, POCreate(supplier_id=supplier.supplier_id, items=[]))


def test_create_draft_rejects_nonpositive_qty(db: Session) -> None:
    supplier = _supplier(db)
    product = create_product(db, _product_create(supplier.supplier_id))
    payload = POCreate(
        supplier_id=supplier.supplier_id,
        items=[
            POLineIn(
                product_id=product.product_id,
                qty_ordered=0,
                unit_price=Decimal("10.00"),
            )
        ],
    )
    with pytest.raises(POError):
        create_draft(db, payload)


def test_create_draft_unknown_supplier_raises(db: Session) -> None:
    supplier = _supplier(db)
    product = create_product(db, _product_create(supplier.supplier_id))
    payload = _po_create(999, product)
    with pytest.raises(LookupError):
        create_draft(db, payload)


def test_place_order_moves_draft_to_ordered(db: Session) -> None:
    supplier = _supplier(db)
    product = create_product(db, _product_create(supplier.supplier_id))
    po = create_draft(db, _po_create(supplier.supplier_id, product))

    ordered = place_order(db, po.po_id)

    assert ordered.status == POStatus.ordered
    assert ordered.order_date is not None


def test_place_order_rejects_non_draft(db: Session) -> None:
    supplier = _supplier(db)
    product = create_product(db, _product_create(supplier.supplier_id))
    po = create_draft(db, _po_create(supplier.supplier_id, product))
    place_order(db, po.po_id)

    with pytest.raises(POError):
        place_order(db, po.po_id)


def test_cancel_order_moves_draft_to_cancelled(db: Session) -> None:
    supplier = _supplier(db)
    product = create_product(db, _product_create(supplier.supplier_id))
    po = create_draft(db, _po_create(supplier.supplier_id, product))

    cancelled = cancel_order(db, po.po_id)

    assert cancelled.status == POStatus.cancelled


def test_cancel_order_rejects_ordered_po(db: Session) -> None:
    supplier = _supplier(db)
    product = create_product(db, _product_create(supplier.supplier_id))
    po = create_draft(db, _po_create(supplier.supplier_id, product))
    place_order(db, po.po_id)

    with pytest.raises(POError):
        cancel_order(db, po.po_id)
