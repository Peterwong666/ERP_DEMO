"""数据看板响应模型。"""

from datetime import date

from pydantic import BaseModel


class DefectShareOut(BaseModel):
    reason_code: str
    reason_label: str
    qty: int


class DashboardOut(BaseModel):
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
    defect_shares: list[DefectShareOut]
    inbound_last_7d: list[int]
    anchor_date: date
