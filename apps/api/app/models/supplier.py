from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import SupplierStatus


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"

    supplier_id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    contact_person: Mapped[str] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(128))
    phone: Mapped[str] = mapped_column(String(32))
    country: Mapped[str] = mapped_column(String(64))
    lead_time_days: Mapped[int]
    status: Mapped[SupplierStatus] = mapped_column(
        Enum(SupplierStatus, native_enum=False, length=32)
    )

    products: Mapped[list["Product"]] = relationship(back_populates="default_supplier")  # noqa: F821
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(  # noqa: F821
        back_populates="supplier"
    )
