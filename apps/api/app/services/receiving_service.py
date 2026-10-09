"""收货：登记收货单并按入库口径过账。

状态机（本模块负责）：PO 已下单/部分收货 → 部分收货 / 已收货；
收货单创建后为「待质检」，后续由质检模块接管。
库存过账全部走 inventory_ledger，本模块不直接改 inventory 表。
"""

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import (
    PurchaseOrderItem,
    ReceivingItem,
    ReceivingOrder,
)
from app.models.enums import POStatus, ReceivingStatus, StockType, TxnType
from app.services import inventory_ledger
from app.services.po_service import OPERATOR, get_purchase_order
from app.services.settings_service import get_setting


class ReceivingError(ValueError):
    pass


def _next_recv_no(db: Session) -> str:
    today = date.today().strftime("%Y%m%d")
    existing = (
        db.query(ReceivingOrder)
        .filter(ReceivingOrder.recv_no.like(f"RCV-{today}-%"))
        .count()
    )
    return f"RCV-{today}-{existing + 1:02d}"


def _collect_qty_by_item(
    po, lines: list[dict]
) -> dict[int, int]:
    """校验每行归属/数量，返回 item_id → 本次收货数（0 数量行跳过）。"""
    items_by_id: dict[int, PurchaseOrderItem] = {
        item.item_id: item for item in po.items
    }
    qty_by_item: dict[int, int] = {}
    for line in lines:
        item = items_by_id.get(line["po_item_id"])
        if item is None:
            raise ReceivingError("收货行不属于该采购单")
        if line["po_item_id"] in qty_by_item:
            raise ReceivingError("同一采购行不能分两条重复提交")
        qty = line["qty_received"]
        if qty < 0:
            raise ReceivingError("收货数量不可为负")
        if qty == 0:
            continue
        if qty > item.qty_ordered - item.qty_received:
            raise ReceivingError("收货数量超过该行未交数量")
        qty_by_item[item.item_id] = qty
    return qty_by_item


def receive_goods(
    db: Session, po_id: int, lines: list[dict]
) -> ReceivingOrder:
    po = get_purchase_order(db, po_id)
    if po.status not in (POStatus.ordered, POStatus.partial_received):
        raise ReceivingError("仅已下单或部分收货的采购单可以收货")
    if not lines:
        raise ReceivingError("收货至少需要一行")

    qty_by_item = _collect_qty_by_item(po, lines)
    if not qty_by_item:
        raise ReceivingError("收货数量必须大于 0")

    caliber = get_setting(db, "inbound_caliber")
    # inspection 口径先进待检，QC 合格才转可售；receiving 口径直达可售
    inbound_stock = (
        StockType.pending if caliber == "inspection" else StockType.available
    )

    recv = ReceivingOrder(
        recv_no=_next_recv_no(db),
        po_id=po.po_id,
        status=ReceivingStatus.pending_inspection,
        received_at=datetime.now(),
        operator=OPERATOR,
        created_by=OPERATOR,
    )
    db.add(recv)
    db.flush()

    items_by_id = {item.item_id: item for item in po.items}
    db.add_all(
        ReceivingItem(
            recv_id=recv.recv_id,
            po_item_id=item_id,
            product_id=items_by_id[item_id].product_id,
            qty_received=qty,
        )
        for item_id, qty in qty_by_item.items()
    )

    for item_id, qty in qty_by_item.items():
        item = items_by_id[item_id]
        item.qty_received += qty
        inventory_ledger.post_transaction(
            db,
            inventory_ledger.LedgerEntry(
                product_id=item.product_id,
                change_qty=qty,
                stock_type=inbound_stock,
                txn_type=TxnType.recv_inbound,
                ref_doc_type="receiving",
                ref_doc_no=recv.recv_no,
                operator=OPERATOR,
            ),
        )

    po.status = (
        POStatus.received
        if all(item.qty_received >= item.qty_ordered for item in po.items)
        else POStatus.partial_received
    )
    db.commit()
    db.refresh(recv)
    return recv
