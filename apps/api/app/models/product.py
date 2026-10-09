from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ProductCategory, ProductStatus


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(primary_key=True)
    sku_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory, native_enum=False, length=32), index=True
    )
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, native_enum=False, length=32)
    )
    unit: Mapped[str] = mapped_column(String(16), default="件")
    standard_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    weight_g: Mapped[int] = mapped_column(Integer)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0)
    default_supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.supplier_id"), index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    default_supplier: Mapped["Supplier"] = relationship(back_populates="products")  # noqa: F821
