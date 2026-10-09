"""数据看板：一个端点返回全部 8 项指标 + 趋势 + 不良分布。"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardOut, DefectShareOut
from app.services.metrics_service import compute_metrics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard(
    anchor: date | None = None,
    db: Session = Depends(get_db),
) -> DashboardOut:
    metrics = compute_metrics(db, anchor=anchor)
    return DashboardOut(
        open_po_count=metrics.open_po_count,
        pending_qc_count=metrics.pending_qc_count,
        inbound_today_qty=metrics.inbound_today_qty,
        available_sku_count=metrics.available_sku_count,
        qc_pass_rate=metrics.qc_pass_rate,
        qc_inspected_today=metrics.qc_inspected_today,
        qc_passed_today=metrics.qc_passed_today,
        low_stock_count=metrics.low_stock_count,
        suggestion_count=metrics.suggestion_count,
        defect_total_today=metrics.defect_total_today,
        defect_shares=[
            DefectShareOut(
                reason_code=share.reason_code,
                reason_label=share.reason_label,
                qty=share.qty,
            )
            for share in metrics.defect_shares
        ],
        inbound_last_7d=list(metrics.inbound_last_7d),
        anchor_date=metrics.anchor_date,
    )
