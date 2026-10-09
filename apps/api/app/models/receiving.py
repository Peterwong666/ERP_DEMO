from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ReceivingStatus


class ReceivingOrder(TimestampMixin, Base):
    __tablename__ = "receiving_orders"

    recv_id: Mapped[int] = mapped_column(primary_key=True)
    recv_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    po_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.po_id"), index=True
    )
    status: Mapped[ReceivingStatus] = mapped_column(
        Enum(ReceivingStatus, native_enum=False, length=32), index=True
    )
    received_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    operator: Mapped[str] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), default="")

    purchase_order: Mapped["PurchaseOrder"] = relationship(  # noqa: F821
        back_populates="receiving_orders"
    )
    items: Mapped[list["ReceivingItem"]] = relationship(
        back_populates="receiving_order", cascade="all, delete-orphan"
    )
    inspection_order: Mapped["InspectionOrder | None"] = relationship(  # noqa: F821
        back_populates="receiving_order"
    )


class ReceivingItem(Base):
    __tablename__ = "receiving_items"

    recv_item_id: Mapped[int] = mapped_column(primary_key=True)
    recv_id: Mapped[int] = mapped_column(
        ForeignKey("receiving_orders.recv_id"), index=True
    )
    po_item_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_order_items.item_id"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id"), index=True
    )
    qty_received: Mapped[int]

    receiving_order: Mapped["ReceivingOrder"] = relationship(back_populates="items")
