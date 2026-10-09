"""补货建议：查看列表、重新生成。"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, ReplenishmentSuggestion
from app.schemas.replenishment import ReplenishmentOut
from app.services.replenishment_service import (
    generate_suggestions,
    list_suggestions,
)

router = APIRouter(prefix="/api/replenishment", tags=["replenishment"])


def _to_out(row: ReplenishmentSuggestion, product: Product) -> ReplenishmentOut:
    return ReplenishmentOut(
        suggestion_id=row.suggestion_id,
        product_id=row.product_id,
        sku_code=product.sku_code,
        name=product.name,
        current_stock=row.current_stock,
        qty_in_transit=row.qty_in_transit,
        forecast_7d=row.forecast_7d,
        suggested_qty=row.suggested_qty,
        days_cover=row.days_cover,
        urgency=row.urgency,
        generated_at=row.generated_at,
    )


def _serialize(db: Session, rows: list[ReplenishmentSuggestion]) -> list[ReplenishmentOut]:
    product_ids = [row.product_id for row in rows]
    products = {
        product.product_id: product
        for product in db.execute(
            select(Product).where(Product.product_id.in_(product_ids))
        ).scalars()
    }
    return [_to_out(row, products[row.product_id]) for row in rows]


@router.get("", response_model=list[ReplenishmentOut])
def get_list(db: Session = Depends(get_db)) -> list[ReplenishmentOut]:
    return _serialize(db, list_suggestions(db))


@router.post("/generate", response_model=list[ReplenishmentOut])
def post_generate(db: Session = Depends(get_db)) -> list[ReplenishmentOut]:
    return _serialize(db, generate_suggestions(db))
