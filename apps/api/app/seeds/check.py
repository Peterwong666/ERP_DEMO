"""make check：核对 8 项看板数字，任一不符以退出码 1 失败。"""

import sys

from app.database import SessionLocal
from app.seeds.builder import ANCHOR
from app.services.metrics_service import compute_metrics

EXPECTED: tuple[tuple[str, int | float], ...] = (
    ("open_po_count", 4),
    ("pending_qc_count", 5),
    ("inbound_today_qty", 1284),
    ("available_sku_count", 50),
    ("qc_pass_rate", 57.1),
    ("low_stock_count", 6),
    ("suggestion_count", 8),
    ("defect_total_today", 102),
)

LABELS = {
    "open_po_count": "待收货 PO",
    "pending_qc_count": "待质检",
    "inbound_today_qty": "今日入库",
    "available_sku_count": "可用库存 SKU",
    "qc_pass_rate": "质检良率",
    "low_stock_count": "低库存预警",
    "suggestion_count": "补货建议",
    "defect_total_today": "不良总数",
}


def main() -> int:
    db = SessionLocal()
    try:
        metrics = compute_metrics(db, anchor=ANCHOR)
    finally:
        db.close()

    all_ok = True
    for field_name, expected in EXPECTED:
        actual = getattr(metrics, field_name)
        ok = actual == expected
        all_ok = all_ok and ok
        mark = "✅" if ok else "❌"
        suffix = "%" if field_name == "qc_pass_rate" else ""
        print(f"{mark} {LABELS[field_name]}：实际 {actual}{suffix} / 目标 {expected}{suffix}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
