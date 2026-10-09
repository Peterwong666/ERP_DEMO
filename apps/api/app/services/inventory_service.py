"""库存台账：余额列表、流水过滤查询、手工调整。"""

from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Inventory, InventoryTransaction, Product
from app.models.enums import StockType, TxnType
from app.services import inventory_ledger

ADJUST_PREFIX = "ADJ-"


class InventoryValidationError(Exception):
    """手工调整入参不合法。"""


@dataclass(frozen=True)
class BalanceRow:
    product_id: int
    sku_code: str
    name: str
    qty_available: int
    qty_pending: int
    qty_defective: int


def list_balances(db: Session) -> list[BalanceRow]:
    rows = db.execute(
        select(Inventory, Product.sku_code, Product.name).join(
            Product, Inventory.product_id == Product.product_id
        )
    ).all()
    return [
        BalanceRow(
            product_id=inventory.product_id,
            sku_code=sku_code,
            name=name,
            qty_available=inventory.qty_available,
            qty_pending=inventory.qty_pending,
            qty_defective=inventory.qty_defective,
        )
        for inventory, sku_code, name in rows
    ]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _parse_date_bound(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InventoryValidationError(f"{field} 日期格式应为 YYYY-MM-DD") from exc


def query_transactions(
    db: Session,
    *,
    product_id: int | None = None,
    txn_type: TxnType | None = None,
    stock_type: StockType | None = None,
    ref_doc_no: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[InventoryTransaction]:
    stmt = select(InventoryTransaction)
    if product_id is not None:
        stmt = stmt.where(InventoryTransaction.product_id == product_id)
    if ref_doc_no:
        pattern = f"%{_escape_like(ref_doc_no)}%"
        stmt = stmt.where(InventoryTransaction.ref_doc_no.like(pattern, escape="\\"))
    if txn_type is not None:
        stmt = stmt.where(InventoryTransaction.txn_type == txn_type)
    if stock_type is not None:
        stmt = stmt.where(InventoryTransaction.stock_type == stock_type)
    if date_from:
        start = datetime.combine(_parse_date_bound(date_from, "起始"), time.min)
        stmt = stmt.where(InventoryTransaction.created_at >= start)
    if date_to:
        end = datetime.combine(_parse_date_bound(date_to, "截止"), time.max)
        stmt = stmt.where(InventoryTransaction.created_at <= end)
    stmt = stmt.order_by(
        InventoryTransaction.created_at.desc(), InventoryTransaction.txn_id.desc()
    )
    return list(db.execute(stmt).scalars().all())


def _next_adjust_no(db: Session, now: datetime) -> str:
    existing = db.execute(
        select(func.count())
        .select_from(InventoryTransaction)
        .where(
            InventoryTransaction.ref_doc_no.like(
                f"{ADJUST_PREFIX}{now:%Y%m%d}-%"
            )
        )
    ).scalar_one()
    return f"{ADJUST_PREFIX}{now:%Y%m%d}-{existing + 1:03d}"


def manual_adjust(
    db: Session,
    product_id: int,
    change_qty: int,
    reason: str,
    *,
    now: datetime | None = None,
) -> InventoryTransaction:
    product = db.get(Product, product_id)
    if product is None:
        raise LookupError(f"商品不存在：{product_id}")
    if change_qty == 0:
        raise InventoryValidationError("调整数量不能为 0")
    if not reason or not reason.strip():
        raise InventoryValidationError("调整原因不能为空")

    moment = now or datetime.now()
    txn_type = (
        TxnType.manual_adjust if change_qty > 0 else TxnType.adjust_outbound
    )
    txn = inventory_ledger.post_transaction(
        db,
        inventory_ledger.LedgerEntry(
            product_id=product_id,
            change_qty=change_qty,
            stock_type=StockType.available,
            txn_type=txn_type,
            ref_doc_type="manual_adjust",
            ref_doc_no=_next_adjust_no(db, moment),
            operator="system",
            reason=reason.strip(),
        ),
    )
    db.commit()
    return txn
