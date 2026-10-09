"""补货建议的 HTTP 契约。"""

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import Urgency
from app.schemas.enum_types import wire_enum


class ReplenishmentOut(BaseModel):
    suggestion_id: int
    product_id: int
    sku_code: str
    name: str
    current_stock: int
    qty_in_transit: int
    forecast_7d: int
    suggested_qty: int
    days_cover: int | None
    urgency: wire_enum(Urgency)
    generated_at: datetime
