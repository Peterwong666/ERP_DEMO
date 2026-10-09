"""质检：按收货单开工、按质检结果过账。

质检单与收货单 1:1。开工时把收货明细复制为质检明细
（qty_inspected = 收货数）。完工按入库口径过账：
- inspection 口径：合格 pending→available，不良 pending→defective
- receiving 口径：合格不动库存（收货时已入可售），不良 available→defective

缺陷数量之和必须等于 检验数 − 合格数。
库存过账全部走 inventory_ledger。
"""

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import (
    DefectRecord,
    InspectionItem,
    InspectionOrder,
    ReceivingOrder,
)
from app.models.enums import (
    DefectReason,
    InspectionStatus,
    ReceivingStatus,
    StockType,
    TxnType,
)
from app.services import inventory_ledger
from app.services.po_service import OPERATOR
from app.services.settings_service import get_setting


class InspectionError(ValueError):
    pass


def _next_insp_no(db: Session) -> str:
    today = date.today().strftime("%Y%m%d")
    existing = (
        db.query(InspectionOrder)
        .filter(InspectionOrder.insp_no.like(f"INSP-{today}-%"))
        .count()
    )
    return f"INSP-{today}-{existing + 1:02d}"


def _get_recv(db: Session, recv_id: int) -> ReceivingOrder:
    recv = db.get(ReceivingOrder, recv_id)
    if recv is None:
        raise LookupError(f"收货单不存在：{recv_id}")
    return recv


def start_inspection(db: Session, recv_id: int) -> InspectionOrder:
    recv = _get_recv(db, recv_id)
    if recv.status != ReceivingStatus.pending_inspection:
        raise InspectionError("仅待质检的收货单可以开工")

    insp = InspectionOrder(
        insp_no=_next_insp_no(db),
        recv_id=recv.recv_id,
        status=InspectionStatus.inspecting,
        inspector=OPERATOR,
        created_by=OPERATOR,
    )
    db.add(insp)
    db.flush()
    db.add_all(
        InspectionItem(
            insp_id=insp.insp_id,
            product_id=recv_item.product_id,
            qty_inspected=recv_item.qty_received,
            qty_passed=0,
            qty_failed=0,
        )
        for recv_item in recv.items
    )
    recv.status = ReceivingStatus.inspecting
    db.commit()
    db.refresh(insp)
    return insp


def _as_reason(value: object) -> DefectReason:
    if isinstance(value, DefectReason):
        return value
    return DefectReason[value]  # type: ignore[index]


def _validate_results(
    insp: InspectionOrder, results: list[dict]
) -> dict[int, dict]:
    """校验结果行归属、合格数、缺陷数之和，返回 insp_item_id → 结果。"""
    items_by_id = {item.insp_item_id: item for item in insp.items}
    if len(results) != len(items_by_id):
        raise InspectionError("质检结果必须覆盖全部质检明细")

    results_by_item: dict[int, dict] = {}
    for result in results:
        item = items_by_id.get(result["insp_item_id"])
        if item is None:
            raise InspectionError("质检结果行不属于该质检单")
        if item.insp_item_id in results_by_item:
            raise InspectionError("质检结果存在重复明细行")
        passed = result["qty_passed"]
        if passed < 0 or passed > item.qty_inspected:
            raise InspectionError("合格数必须在 0 与检验数之间")

        defects = [
            (_as_reason(row["reason_code"]), row["qty"])
            for row in result["defects"]
        ]
        if any(qty <= 0 for _, qty in defects):
            raise InspectionError("缺陷数量必须大于 0")
        failed = item.qty_inspected - passed
        if sum(qty for _, qty in defects) != failed:
            raise InspectionError("缺陷数量之和必须等于 检验数−合格数")

        results_by_item[item.insp_item_id] = {
            "passed": passed,
            "failed": failed,
            "defects": defects,
        }
    return results_by_item


def _post_quality_moves(
    db: Session,
    insp: InspectionOrder,
    item: InspectionItem,
    passed: int,
    failed: int,
) -> None:
    caliber = get_setting(db, "inbound_caliber")
    entry_args = {
        "ref_doc_type": "inspection",
        "ref_doc_no": insp.insp_no,
        "operator": OPERATOR,
    }
    if caliber == "inspection":
        # 收货时入的是待检：合格与不良都从 pending 转出
        if passed > 0:
            inventory_ledger.post_transaction(
                db,
                inventory_ledger.LedgerEntry(
                    product_id=item.product_id,
                    change_qty=-passed,
                    stock_type=StockType.pending,
                    txn_type=TxnType.qc_pass,
                    **entry_args,
                ),
            )
            inventory_ledger.post_transaction(
                db,
                inventory_ledger.LedgerEntry(
                    product_id=item.product_id,
                    change_qty=passed,
                    stock_type=StockType.available,
                    txn_type=TxnType.qc_pass,
                    **entry_args,
                ),
            )
        if failed > 0:
            inventory_ledger.post_transaction(
                db,
                inventory_ledger.LedgerEntry(
                    product_id=item.product_id,
                    change_qty=-failed,
                    stock_type=StockType.pending,
                    txn_type=TxnType.qc_fail,
                    **entry_args,
                ),
            )
    elif failed > 0:
        # receiving 口径：合格部分收货时已入可售，不动库存；
        # 不良从可售转不良品
        inventory_ledger.post_transaction(
            db,
            inventory_ledger.LedgerEntry(
                product_id=item.product_id,
                change_qty=-failed,
                stock_type=StockType.available,
                txn_type=TxnType.qc_fail,
                **entry_args,
            ),
        )

    if failed > 0:
        inventory_ledger.post_transaction(
            db,
            inventory_ledger.LedgerEntry(
                product_id=item.product_id,
                change_qty=failed,
                stock_type=StockType.defective,
                txn_type=TxnType.qc_fail,
                **entry_args,
            ),
        )


def complete_inspection(
    db: Session, insp_id: int, results: list[dict]
) -> InspectionOrder:
    insp = db.get(InspectionOrder, insp_id)
    if insp is None:
        raise LookupError(f"质检单不存在：{insp_id}")
    if insp.status != InspectionStatus.inspecting:
        raise InspectionError("仅质检中的单据可以录入结果")

    results_by_item = _validate_results(insp, results)

    for item in insp.items:
        result = results_by_item[item.insp_item_id]
        passed = result["passed"]
        failed = result["failed"]
        item.qty_passed = passed
        item.qty_failed = failed
        db.add_all(
            DefectRecord(
                insp_item_id=item.insp_item_id,
                reason_code=reason,
                qty=qty,
            )
            for reason, qty in result["defects"]
        )
        _post_quality_moves(db, insp, item, passed, failed)

    insp.status = InspectionStatus.completed
    insp.inspected_at = datetime.now()
    insp.receiving_order.status = ReceivingStatus.completed
    db.commit()
    db.refresh(insp)
    return insp
