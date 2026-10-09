"""采购单：草稿创建与下单/取消状态流转。

状态机（本模块只管理）：草稿 → 已下单 / 已取消。
收货触发的「部分收货/已收货」由收货模块负责。
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Product, PurchaseOrder, PurchaseOrderItem, Supplier
from app.models.enums import POStatus
from app.schemas.products import POCreate

OPERATOR = "系统"


class POError(ValueError):
    pass


def _next_po_no(db: Session) -> str:
    today = date.today().strftime("%Y%m%d")
    existing = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.po_no.like(f"PO-{today}-%"))
        .count()
    )
    return f"PO-{today}-{existing + 1:02d}"


def _validate_lines(db: Session, payload: POCreate) -> None:
    if not payload.items:
        raise POError("采购单至少需要一行")
    for line in payload.items:
        if line.qty_ordered <= 0:
            raise POError("采购数量必须大于 0")
        if line.unit_price < 0:
            raise POError("单价不可为负")
        if db.get(Product, line.product_id) is None:
            raise LookupError(f"产品不存在：{line.product_id}")


def create_draft(db: Session, payload: POCreate) -> PurchaseOrder:
    _validate_lines(db, payload)
    supplier = db.get(Supplier, payload.supplier_id)
    if supplier is None:
        raise LookupError(f"供应商不存在：{payload.supplier_id}")

    po = PurchaseOrder(
        po_no=_next_po_no(db),
        supplier_id=payload.supplier_id,
        status=POStatus.draft,
        total_amount=sum(
            line.qty_ordered * line.unit_price for line in payload.items
        ),
        order_date=date.today(),
        expected_date=date.today() + timedelta(days=supplier.lead_time_days),
        notes=payload.notes,
        created_by=OPERATOR,
    )
    db.add(po)
    db.flush()
    db.add_all(
        PurchaseOrderItem(
            po_id=po.po_id,
            product_id=line.product_id,
            qty_ordered=line.qty_ordered,
            qty_received=0,
            unit_price=line.unit_price,
        )
        for line in payload.items
    )
    db.commit()
    db.refresh(po)
    return po


def list_purchase_orders(db: Session) -> list[PurchaseOrder]:
    return db.query(PurchaseOrder).order_by(PurchaseOrder.po_id.desc()).all()


def get_purchase_order(db: Session, po_id: int) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise LookupError(f"采购单不存在：{po_id}")
    return po


def place_order(db: Session, po_id: int) -> PurchaseOrder:
    po = get_purchase_order(db, po_id)
    if po.status != POStatus.draft:
        raise POError("仅草稿状态的采购单可以下单")
    po.status = POStatus.ordered
    db.commit()
    db.refresh(po)
    return po


def cancel_order(db: Session, po_id: int) -> PurchaseOrder:
    po = get_purchase_order(db, po_id)
    if po.status != POStatus.draft:
        raise POError("仅草稿状态的采购单可以取消")
    po.status = POStatus.cancelled
    db.commit()
    db.refresh(po)
    return po
