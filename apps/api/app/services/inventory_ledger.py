"""库存过账共享模块：流水与物化余额的唯一写入口。

不变量：每个 (product_id, stock_type) 的 Inventory 物化余额
恒等于该维度全部 InventoryTransaction.change_qty 之和，且永不为负。

事务约定：本模块只 flush 不 commit；多笔过账的原子性由调用方保证。
rebuild_inventory 就地重建后会 expire_all：此前加载的 Inventory 实例
再次访问时刷新，调用方不要缓存重建前的数量。
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Inventory, InventoryTransaction
from app.models.enums import StockType, TxnType

_QTY_FIELD: dict[StockType, str] = {
    StockType.available: "qty_available",
    StockType.pending: "qty_pending",
    StockType.defective: "qty_defective",
}


class LedgerError(ValueError):
    pass


@dataclass(frozen=True)
class LedgerEntry:
    product_id: int
    change_qty: int
    stock_type: StockType
    txn_type: TxnType
    ref_doc_type: str
    ref_doc_no: str
    operator: str
    reason: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class ReconciliationMismatch:
    product_id: int
    stock_type: StockType
    book_qty: int
    ledger_qty: int


def _shortage_error(stock_type: StockType, current: int, change_qty: int) -> LedgerError:
    return LedgerError(
        f"{stock_type.value} 余额不足：当前 {current}，本次变动 {change_qty}"
    )


def _open_or_insert(db: Session, entry: LedgerEntry) -> None:
    """条件 UPDATE 未命中：区分余额不足与行不存在（后者插入）。"""
    qty_field = _QTY_FIELD[entry.stock_type]
    inventory = (
        db.query(Inventory).filter_by(product_id=entry.product_id).one_or_none()
    )
    if inventory is None:
        if entry.change_qty < 0:
            raise _shortage_error(entry.stock_type, 0, entry.change_qty)
        values = {
            "product_id": entry.product_id,
            "qty_available": 0,
            "qty_pending": 0,
            "qty_defective": 0,
            qty_field: entry.change_qty,
        }
        db.add(Inventory(**values))
        try:
            db.flush()
        except IntegrityError as exc:
            # 并发首过：事务已被 DB 错误置为需 rollback，调用方须
            # db.rollback() 后重试（普通余额不足路径无此要求）
            raise LedgerError(
                "该 SKU 正在被并发过账，请 rollback 后重试"
            ) from exc
        return

    raise _shortage_error(
        entry.stock_type, getattr(inventory, qty_field), entry.change_qty
    )


def post_transaction(db: Session, entry: LedgerEntry) -> InventoryTransaction:
    if entry.change_qty == 0:
        raise LedgerError("过账数量不能为 0")

    qty_column = getattr(Inventory, _QTY_FIELD[entry.stock_type])
    # 原子条件 UPDATE：行存在且更新后非负才命中，把"读-校验-写"
    # 收敛为单条 SQL，对 SQLite/Postgres 均无 TOCTOU 窗口
    result = db.execute(
        update(Inventory)
        .where(
            Inventory.product_id == entry.product_id,
            qty_column + entry.change_qty >= 0,
        )
        .values({qty_column: qty_column + entry.change_qty})
    )
    if result.rowcount == 0:
        _open_or_insert(db, entry)

    txn = InventoryTransaction(
        product_id=entry.product_id,
        change_qty=entry.change_qty,
        stock_type=entry.stock_type,
        txn_type=entry.txn_type,
        ref_doc_type=entry.ref_doc_type,
        ref_doc_no=entry.ref_doc_no,
        reason=entry.reason,
        operator=entry.operator,
        created_at=entry.created_at or datetime.now(),
    )
    db.add(txn)
    db.flush()
    return txn


def _ledger_sums(
    db: Session,
) -> dict[tuple[int, StockType], int]:
    """按 (product_id, stock_type) 汇总全部流水净额。"""
    rows = db.execute(
        select(
            InventoryTransaction.product_id,
            InventoryTransaction.stock_type,
            func.sum(InventoryTransaction.change_qty),
        ).group_by(
            InventoryTransaction.product_id, InventoryTransaction.stock_type
        )
    ).all()
    return {
        (product_id, stock_type): int(total) for product_id, stock_type, total in rows
    }


def rebuild_inventory(db: Session) -> int:
    """按流水就地重建物化余额：更新现有行、补缺失行、删多余行。

    保留主键、不整表删除；结束后 expire_all，调用方此前持有的
    Inventory 实例再次访问时会刷新为重建后的数值。
    """
    sums = _ledger_sums(db)

    balances: dict[int, dict[StockType, int]] = {}
    for (product_id, stock_type), total in sums.items():
        balances.setdefault(
            product_id,
            {StockType.available: 0, StockType.pending: 0, StockType.defective: 0},
        )[stock_type] = total

    existing = {
        inventory.product_id: inventory for inventory in db.query(Inventory).all()
    }
    for product_id in existing.keys() - balances.keys():
        db.delete(existing[product_id])
    for product_id, qty in balances.items():
        inventory = existing.get(product_id) or Inventory(product_id=product_id)
        inventory.qty_available = qty[StockType.available]
        inventory.qty_pending = qty[StockType.pending]
        inventory.qty_defective = qty[StockType.defective]
        db.add(inventory)

    db.flush()
    db.expire_all()
    return len(balances)


def find_reconciliation_mismatches(db: Session) -> list[ReconciliationMismatch]:
    sums = _ledger_sums(db)
    inventories = db.query(Inventory).all()
    inventory_by_product = {row.product_id: row for row in inventories}

    # 流水维度与物化行的并集：既查数值漂移，也查"整行缺失"
    dimensions: set[tuple[int, StockType]] = set(sums)
    for product_id in inventory_by_product:
        dimensions.update((product_id, stock_type) for stock_type in _QTY_FIELD)

    mismatches: list[ReconciliationMismatch] = []
    for product_id, stock_type in dimensions:
        qty_field = _QTY_FIELD[stock_type]
        book_qty = getattr(
            inventory_by_product.get(product_id), qty_field, 0
        )
        ledger_qty = sums.get((product_id, stock_type), 0)
        if book_qty != ledger_qty:
            mismatches.append(
                ReconciliationMismatch(
                    product_id=product_id,
                    stock_type=stock_type,
                    book_qty=book_qty,
                    ledger_qty=ledger_qty,
                )
            )
    return mismatches
