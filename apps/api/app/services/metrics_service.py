"""看板指标计算：8 项数字的唯一计算来源。

核对脚本与 /api/dashboard 共用本模块，保证"核对的数字"与"展示的数字"一致。
阈值参数全部从 system_settings 读取，不硬编码。
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    DefectRecord,
    InspectionItem,
    InspectionOrder,
    Inventory,
    PurchaseOrder,
    ReceivingItem,
    ReceivingOrder,
)
from app.models.enums import POStatus, ReceivingStatus
from app.services.settings_service import get_setting
from app.services.stock_analytics import find_low_stock, select_candidates


@dataclass(frozen=True)
class DefectShare:
    reason_code: str
    reason_label: str
    qty: int


@dataclass(frozen=True)
class DashboardMetrics:
    open_po_count: int
    pending_qc_count: int
    inbound_today_qty: int
    available_sku_count: int
    qc_pass_rate: float
    qc_inspected_today: int
    qc_passed_today: int
    low_stock_count: int
    suggestion_count: int
    defect_total_today: int
    defect_shares: tuple[DefectShare, ...]
    inbound_last_7d: tuple[int, ...]
    anchor_date: date


def _inbound_by_day(db: Session, day: date) -> int:
    total = db.execute(
        select(func.coalesce(func.sum(ReceivingItem.qty_received), 0))
        .join(ReceivingOrder, ReceivingItem.recv_id == ReceivingOrder.recv_id)
        .where(func.date(ReceivingOrder.received_at) == day)
    ).scalar_one()
    return int(total)


def compute_metrics(db: Session, anchor: date | None = None) -> DashboardMetrics:
    anchor = anchor or settings.data_anchor_date

    caliber = str(get_setting(db, "inbound_caliber"))

    # 1. 待收货 PO
    open_po_count = int(
        db.execute(
            select(func.count())
            .select_from(PurchaseOrder)
            .where(PurchaseOrder.status.in_([POStatus.ordered, POStatus.partial_received]))
        ).scalar_one()
    )

    # 2. 待质检（今日到货且未完成质检的收货批）
    pending_qc_count = int(
        db.execute(
            select(func.count())
            .select_from(ReceivingOrder)
            .where(
                func.date(ReceivingOrder.received_at) == anchor,
                ReceivingOrder.status.in_(
                    [ReceivingStatus.pending_inspection, ReceivingStatus.inspecting]
                ),
            )
        ).scalar_one()
    )

    # 3. 今日入库（业务口径可切换）
    if caliber == "inspection":
        inbound_today_qty = int(
            db.execute(
                select(func.coalesce(func.sum(InspectionItem.qty_passed), 0))
                .join(InspectionOrder, InspectionItem.insp_id == InspectionOrder.insp_id)
                .where(func.date(InspectionOrder.inspected_at) == anchor)
            ).scalar_one()
        )
    else:
        inbound_today_qty = _inbound_by_day(db, anchor)

    # 4. 可用库存 SKU 数
    available_map = {
        product_id: qty
        for product_id, qty in db.execute(
            select(Inventory.product_id, Inventory.qty_available)
        ).all()
    }
    available_sku_count = sum(1 for qty in available_map.values() if qty > 0)

    # 5. 今日质检良率
    inspected_today, passed_today = (
        db.execute(
            select(
                func.coalesce(func.sum(InspectionItem.qty_inspected), 0),
                func.coalesce(func.sum(InspectionItem.qty_passed), 0),
            )
            .select_from(InspectionItem)
            .join(InspectionOrder, InspectionItem.insp_id == InspectionOrder.insp_id)
            .where(func.date(InspectionOrder.inspected_at) == anchor)
        ).one()
    )
    inspected_today = int(inspected_today)
    passed_today = int(passed_today)
    qc_pass_rate = (
        round(passed_today / inspected_today * 100, 1) if inspected_today else 0.0
    )

    # 6 & 7. 低库存 / 补货候选（与补货引擎同源）
    low_stock_count = len(find_low_stock(db, anchor))
    suggestion_count = len(select_candidates(db, anchor))

    # 8. 今日不良总数与原因分布
    defect_rows = db.execute(
        select(DefectRecord.reason_code, func.sum(DefectRecord.qty))
        .join(InspectionItem, DefectRecord.insp_item_id == InspectionItem.insp_item_id)
        .join(InspectionOrder, InspectionItem.insp_id == InspectionOrder.insp_id)
        .where(func.date(InspectionOrder.inspected_at) == anchor)
        .group_by(DefectRecord.reason_code)
    ).all()
    defect_shares = tuple(
        DefectShare(
            reason_code=reason.name, reason_label=reason.value, qty=int(qty)
        )
        for reason, qty in sorted(defect_rows, key=lambda row: -row[1])
    )
    defect_total_today = sum(share.qty for share in defect_shares)

    # 历史趋势固定收货口径；仅「今日」格跟随可切换口径，
    # 保证趋势末柱与「今日入库」卡片一致
    inbound_last_7d = tuple(
        _inbound_by_day(db, anchor - timedelta(days=offset))
        for offset in range(6, -1, -1)
    )
    if caliber == "inspection":
        inbound_last_7d = inbound_last_7d[:-1] + (inbound_today_qty,)

    return DashboardMetrics(
        open_po_count=open_po_count,
        pending_qc_count=pending_qc_count,
        inbound_today_qty=inbound_today_qty,
        available_sku_count=available_sku_count,
        qc_pass_rate=qc_pass_rate,
        qc_inspected_today=inspected_today,
        qc_passed_today=passed_today,
        low_stock_count=low_stock_count,
        suggestion_count=suggestion_count,
        defect_total_today=defect_total_today,
        defect_shares=defect_shares,
        inbound_last_7d=inbound_last_7d,
        anchor_date=anchor,
    )
