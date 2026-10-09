"""补货规则引擎：按近 7 日销量预测生成/刷新补货建议。

候选筛选与紧急度规则全部在 stock_analytics，本模块只负责
把计算结果落地为 ReplenishmentSuggestion（upsert + 清理过期行）。
"""

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ReplenishmentSuggestion
from app.services.settings_service import get_setting
from app.services.stock_analytics import (
    SALES_AVG_WINDOW_DAYS,
    TARGET_COVER_DAYS,
    ProductStock,
    classify_urgency,
    select_candidates,
)


def list_suggestions(db: Session) -> list[ReplenishmentSuggestion]:
    return list(
        db.execute(
            select(ReplenishmentSuggestion).order_by(
                ReplenishmentSuggestion.days_cover.asc(),
                ReplenishmentSuggestion.suggestion_id.asc(),
            )
        ).scalars().all()
    )


def _build_values(
    stock: ProductStock,
    emergency_days: int,
    suggest_days: int,
    moment: datetime,
) -> dict[str, int | str | datetime | None]:
    cover = stock.days_cover
    target_qty = round(stock.avg_daily * TARGET_COVER_DAYS)
    suggested_qty = max(0, target_qty - stock.available - stock.in_transit)
    return {
        "current_stock": stock.available,
        "qty_in_transit": stock.in_transit,
        "forecast_7d": round(stock.avg_daily * SALES_AVG_WINDOW_DAYS),
        "suggested_qty": suggested_qty,
        "days_cover": round(cover) if cover is not None else None,
        "urgency": classify_urgency(cover, emergency_days, suggest_days),
        "generated_at": moment,
    }


def generate_suggestions(
    db: Session, anchor: date | None = None
) -> list[ReplenishmentSuggestion]:
    anchor = anchor or settings.data_anchor_date
    emergency_days = int(get_setting(db, "urgency_emergency_days"))
    suggest_days = int(get_setting(db, "urgency_suggestion_days"))

    moment = datetime.now()
    existing = {
        row.product_id: row
        for row in db.execute(select(ReplenishmentSuggestion)).scalars().all()
    }
    candidate_ids: set[int] = set()
    for stock in select_candidates(db, anchor):
        product_id = stock.product.product_id
        candidate_ids.add(product_id)
        values = _build_values(stock, emergency_days, suggest_days, moment)
        current = existing.get(product_id)
        if current is None:
            db.add(ReplenishmentSuggestion(product_id=product_id, **values))
        else:
            for field, value in values.items():
                setattr(current, field, value)

    for product_id, row in existing.items():
        if product_id not in candidate_ids:
            db.delete(row)

    db.commit()
    return list_suggestions(db)
