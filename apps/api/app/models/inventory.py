from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import StockType, TxnType


class Inventory(TimestampMixin, Base):
    __tablename__ = "inventory"

    inventory_id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id"), unique=True, index=True
    )
    qty_available: Mapped[int] = mapped_column(default=0)
    qty_pending: Mapped[int] = mapped_column(default=0)
    qty_defective: Mapped[int] = mapped_column(default=0)
    location: Mapped[str | None] = mapped_column(String(32), nullable=True)


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    txn_id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id"), index=True
    )
    change_qty: Mapped[int]
    stock_type: Mapped[StockType] = mapped_column(
        Enum(StockType, native_enum=False, length=16)
    )
    txn_type: Mapped[TxnType] = mapped_column(
        Enum(TxnType, native_enum=False, length=32)
    )
    ref_doc_type: Mapped[str] = mapped_column(String(16))
    ref_doc_no: Mapped[str] = mapped_column(String(32), index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operator: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
