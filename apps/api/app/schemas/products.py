"""产品与采购单的请求/响应 schema。"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import POStatus, ProductCategory, ProductStatus
from app.schemas.enum_types import wire_enum

# ---------- 产品 ----------

class ProductCreate(BaseModel):
    sku_code: str
    name: str
    category: wire_enum(ProductCategory)
    unit: str = "件"
    standard_cost: Decimal
    weight_g: int
    safety_stock: int = 0
    default_supplier_id: int
    barcode: str | None = None
    description: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    category: wire_enum(ProductCategory) | None = None
    unit: str | None = None
    standard_cost: Decimal | None = None
    weight_g: int | None = None
    safety_stock: int | None = None
    barcode: str | None = None
    description: str | None = None


class ProductStatusUpdate(BaseModel):
    status: wire_enum(ProductStatus)


class ProductOut(BaseModel):
    product_id: int
    sku_code: str
    name: str
    category: wire_enum(ProductCategory)
    status: wire_enum(ProductStatus)
    unit: str
    standard_cost: Decimal
    weight_g: int
    safety_stock: int
    default_supplier_id: int
    barcode: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


# ---------- 采购单 ----------

class POLineIn(BaseModel):
    product_id: int
    qty_ordered: int
    unit_price: Decimal


class POCreate(BaseModel):
    supplier_id: int
    items: list[POLineIn]
    notes: str | None = None


class POLineOut(BaseModel):
    item_id: int
    product_id: int
    qty_ordered: int
    qty_received: int
    unit_price: Decimal

    model_config = {"from_attributes": True}


class POOut(BaseModel):
    po_id: int
    po_no: str
    supplier_id: int
    status: wire_enum(POStatus)
    total_amount: Decimal
    order_date: date | None = None
    expected_date: date | None = None
    notes: str | None = None
    created_by: str
    items: list[POLineOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}
