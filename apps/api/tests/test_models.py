from datetime import date
from decimal import Decimal

import pytest
from app.models import (
    DailySales,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
)
from app.models.enums import POStatus, ProductCategory, ProductStatus, SupplierStatus
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def make_supplier(db: Session, code: str = "SUP-001") -> Supplier:
    supplier = Supplier(
        code=code,
        name="测试供应商",
        contact_person="张三",
        email="test@example.com",
        phone="13800000000",
        country="中国",
        lead_time_days=15,
        status=SupplierStatus.active,
    )
    db.add(supplier)
    db.commit()
    return supplier


def make_product(db: Session, supplier: Supplier, sku: str = "EC-0001") -> Product:
    product = Product(
        sku_code=sku,
        name="测试商品",
        category=ProductCategory.electronics,
        status=ProductStatus.on_sale,
        unit="件",
        standard_cost=Decimal("12.50"),
        weight_g=120,
        safety_stock=10,
        default_supplier_id=supplier.supplier_id,
    )
    db.add(product)
    db.commit()
    return product


def test_supplier_code_unique_constraint(db: Session) -> None:
    # Arrange
    make_supplier(db)

    # Act & Assert
    db.add(
        Supplier(
            code="SUP-001",
            name="重复编码",
            contact_person="李四",
            email="dup@example.com",
            phone="13900000000",
            country="中国",
            lead_time_days=7,
            status=SupplierStatus.active,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_purchase_order_items_cascade_delete(db: Session) -> None:
    # Arrange
    supplier = make_supplier(db)
    product = make_product(db, supplier)
    po = PurchaseOrder(
        po_no="PO-001",
        supplier_id=supplier.supplier_id,
        status=POStatus.ordered,
        order_date=date(2026, 10, 9),
        created_by="测试员",
    )
    po.items.append(
        PurchaseOrderItem(
            product_id=product.product_id,
            qty_ordered=100,
            unit_price=Decimal("12.50"),
        )
    )
    db.add(po)
    db.commit()

    # Act
    db.delete(po)
    db.commit()

    # Assert
    assert db.query(PurchaseOrderItem).count() == 0


def test_purchase_order_item_qty_received_defaults_zero(db: Session) -> None:
    # Arrange
    supplier = make_supplier(db)
    product = make_product(db, supplier)
    item = PurchaseOrderItem(
        po_id=1,
        product_id=product.product_id,
        qty_ordered=50,
        unit_price=Decimal("9.90"),
    )

    # Act & Assert — flush applies Python-side defaults without a parent row
    db.add(item)
    db.flush()
    assert item.qty_received == 0


def test_supplier_products_relationship(db: Session) -> None:
    # Arrange
    supplier = make_supplier(db)
    make_product(db, supplier)

    # Act & Assert
    loaded = db.get(Supplier, supplier.supplier_id)
    assert loaded is not None
    assert [product.sku_code for product in loaded.products] == ["EC-0001"]
    assert loaded.products[0].default_supplier.code == "SUP-001"


def test_daily_sales_product_date_unique(db: Session) -> None:
    # Arrange
    supplier = make_supplier(db)
    product = make_product(db, supplier)
    day = date(2026, 10, 9)
    db.add(DailySales(product_id=product.product_id, date=day, qty_sold=5))
    db.commit()

    # Act & Assert
    db.add(DailySales(product_id=product.product_id, date=day, qty_sold=3))
    with pytest.raises(IntegrityError):
        db.commit()
