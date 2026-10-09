"""库存分析共享原语：销量、在途、覆盖天数、低库存、补货候选与紧急度。

看板指标与补货引擎共用本模块，保证两处的低库存数、建议数同源。
阈值参数全部从 system_settings 读取，不硬编码。
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    DailySales,
    Inventory,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
)
from app.models.enums import POStatus, Urgency
from app.services.settings_service import get_setting

# 正常态补货的目标覆盖天数 / 近 7 日均值窗口（业务常量，非阈值参数）
TARGET_COVER_DAYS = 30
SALES_AVG_WINDOW_DAYS = 7


@dataclass(frozen=True)
class ProductStock:
    product: Product
    available: int
    avg_daily: float
    in_transit: int

    @property
    def days_cover(self) -> int | None:
        # 完整可售天数（向下取整，保守口径），与 days_cover 整数列一致
        if self.avg_daily <= 0:
            return None
        return int(self.available // self.avg_daily)




def avg_daily_sales(db: Session, anchor: date) -> dict[int, float]:
    """近 7 日（anchor 前 7 天，缺销日按 0）平均销量。"""
    start = anchor - timedelta(days=SALES_AVG_WINDOW_DAYS)
    rows = db.execute(
        select(DailySales.product_id, func.sum(DailySales.qty_sold))
        .where(DailySales.date >= start, DailySales.date < anchor)
        .group_by(DailySales.product_id)
    ).all()
    return {
        product_id: total / SALES_AVG_WINDOW_DAYS for product_id, total in rows
    }


def in_transit_qty(db: Session) -> dict[int, int]:
    """在途量：未结 PO 行的 (已订 − 已收) 合计。"""
    rows = db.execute(
        select(
            PurchaseOrderItem.product_id,
            func.sum(PurchaseOrderItem.qty_ordered - PurchaseOrderItem.qty_received),
        )
        .join(PurchaseOrder, PurchaseOrderItem.po_id == PurchaseOrder.po_id)
        .where(
            PurchaseOrder.status.in_([POStatus.ordered, POStatus.partial_received])
        )
        .group_by(PurchaseOrderItem.product_id)
    ).all()
    return {product_id: total for product_id, total in rows}


def available_qty(db: Session) -> dict[int, int]:
    return {
        product_id: qty
        for product_id, qty in db.execute(
            select(Inventory.product_id, Inventory.qty_available)
        ).all()
    }


def iter_product_stock(db: Session, anchor: date) -> list[ProductStock]:
    avg_map = avg_daily_sales(db, anchor)
    transit_map = in_transit_qty(db)
    available_map = available_qty(db)
    products = db.execute(select(Product)).scalars().all()
    return [
        ProductStock(
            product=product,
            available=available_map.get(product.product_id, 0),
            avg_daily=avg_map.get(product.product_id, 0.0),
            in_transit=transit_map.get(product.product_id, 0),
        )
        for product in products
    ]


def find_low_stock(
    db: Session, anchor: date
) -> list[tuple[Product, int | None, int]]:
    """低库存行：(商品, 覆盖天数, 可用量)。

    判定：可用 ≤ 安全库存，或覆盖天数低于阈值。
    """
    threshold = int(get_setting(db, "low_stock_days_threshold"))
    rows = [
        (stock.product, stock.days_cover, stock.available)
        for stock in iter_product_stock(db, anchor)
        if stock.available <= stock.product.safety_stock
        or (stock.days_cover is not None and stock.days_cover < threshold)
    ]
    return sorted(rows, key=lambda row: (row[1] is None, row[1]))


def is_suggestion_candidate(stock: ProductStock, suggest_days: int) -> bool:
    """覆盖低于建议天数，或 30 天目标量（含在途）仍有缺口。"""
    gap_to_target = (
        stock.avg_daily * TARGET_COVER_DAYS
        - stock.available
        - stock.in_transit
    )
    return (
        stock.days_cover is not None and stock.days_cover < suggest_days
    ) or gap_to_target > 0


def select_candidates(db: Session, anchor: date) -> list[ProductStock]:
    suggest_days = int(get_setting(db, "urgency_suggestion_days"))
    return [
        stock
        for stock in iter_product_stock(db, anchor)
        if is_suggestion_candidate(stock, suggest_days)
    ]


def classify_urgency(
    days_cover: float | None,
    emergency_days: int,
    suggest_days: int,
) -> Urgency:
    if days_cover is not None and days_cover <= emergency_days:
        return Urgency.emergency
    if days_cover is not None and days_cover <= suggest_days:
        return Urgency.suggest
    return Urgency.normal
