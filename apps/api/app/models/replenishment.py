from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import Urgency


class ReplenishmentSuggestion(Base):
    __tablename__ = "replenishment_suggestions"

    suggestion_id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id"), unique=True, index=True
    )
    current_stock: Mapped[int]
    qty_in_transit: Mapped[int]
    forecast_7d: Mapped[int]
    suggested_qty: Mapped[int]
    days_cover: Mapped[int]
    urgency: Mapped[Urgency] = mapped_column(
        Enum(Urgency, native_enum=False, length=16), index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime)
