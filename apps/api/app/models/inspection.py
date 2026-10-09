from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import DefectReason, InspectionStatus


class InspectionOrder(TimestampMixin, Base):
    __tablename__ = "inspection_orders"

    insp_id: Mapped[int] = mapped_column(primary_key=True)
    insp_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    recv_id: Mapped[int] = mapped_column(
        ForeignKey("receiving_orders.recv_id"), unique=True, index=True
    )
    status: Mapped[InspectionStatus] = mapped_column(
        Enum(InspectionStatus, native_enum=False, length=32), index=True
    )
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    inspector: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(64), default="")

    receiving_order: Mapped["ReceivingOrder"] = relationship(  # noqa: F821
        back_populates="inspection_order"
    )
    items: Mapped[list["InspectionItem"]] = relationship(
        back_populates="inspection_order", cascade="all, delete-orphan"
    )


class InspectionItem(Base):
    __tablename__ = "inspection_items"

    insp_item_id: Mapped[int] = mapped_column(primary_key=True)
    insp_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_orders.insp_id"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.product_id"), index=True
    )
    qty_inspected: Mapped[int]
    qty_passed: Mapped[int]
    qty_failed: Mapped[int]

    inspection_order: Mapped["InspectionOrder"] = relationship(back_populates="items")
    defect_records: Mapped[list["DefectRecord"]] = relationship(
        back_populates="inspection_item", cascade="all, delete-orphan"
    )


class DefectRecord(Base):
    __tablename__ = "defect_records"

    defect_id: Mapped[int] = mapped_column(primary_key=True)
    insp_item_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_items.insp_item_id"), index=True
    )
    reason_code: Mapped[DefectReason] = mapped_column(
        Enum(DefectReason, native_enum=False, length=32), index=True
    )
    qty: Mapped[int]

    inspection_item: Mapped["InspectionItem"] = relationship(
        back_populates="defect_records"
    )
