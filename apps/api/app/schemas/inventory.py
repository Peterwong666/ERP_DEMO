"""库存台账的 HTTP 契约：余额、流水、手工调整、对账、低库存。"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import StockType, TxnType
from app.schemas.enum_types import wire_enum


class BalanceOut(BaseModel):
    product_id: int
    sku_code: str
    name: str
    qty_available: int
    qty_pending: int
    qty_defective: int


class TransactionOut(BaseModel):
    txn_id: int
    product_id: int
    change_qty: int
    stock_type: wire_enum(StockType)
    txn_type: wire_enum(TxnType)
    ref_doc_type: str
    ref_doc_no: str
    reason: str | None
    operator: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AdjustIn(BaseModel):
    product_id: int
    change_qty: int
    reason: str = Field(max_length=255)


class ReconciliationOut(BaseModel):
    product_id: int
    stock_type: wire_enum(StockType)
    book_qty: int
    ledger_qty: int


class LowStockOut(BaseModel):
    product_id: int
    sku_code: str
    name: str
    days_cover: float | None
    qty_available: int
    safety_stock: int
