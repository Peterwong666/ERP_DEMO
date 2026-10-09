from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DailySales(Base):
    __tablename__ = "daily_sales"
    __table_args__ = (
        UniqueConstraint("product_id", "date", name="uq_sales_product_date"),
    )

    sales_id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    qty_sold: Mapped[int]
