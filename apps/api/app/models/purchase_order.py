from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import POStatus


class PurchaseOrder(TimestampMixin, Base):
    __tablename__ = "purchase_orders"

    po_id: Mapped[int] = mapped_column(primary_key=True)
    po_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.supplier_id"), index=True
    )
    status: Mapped[POStatus] = mapped_column(
        Enum(POStatus, native_enum=False, length=32), index=True
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    order_date: Mapped[Date] = mapped_column(Date)
    expected_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), default="")

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")  # noqa: F821
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )
    receiving_orders: Mapped[list["ReceivingOrder"]] = relationship(  # noqa: F821
        back_populates="purchase_order"
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    item_id: Mapped[int] = mapped_column(primary_key=True)
    po_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.po_id"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id"), index=True
    )
    qty_ordered: Mapped[int]
    qty_received: Mapped[int] = mapped_column(default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
