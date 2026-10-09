"""收货 + 质检的 HTTP 契约。"""

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import (
    DefectReason,
    InspectionStatus,
    ReceivingStatus,
)
from app.schemas.enum_types import wire_enum


class ReceivingLineIn(BaseModel):
    po_item_id: int
    qty_received: int


class ReceivingCreate(BaseModel):
    lines: list[ReceivingLineIn]


class ReceivingItemOut(BaseModel):
    recv_item_id: int
    po_item_id: int
    product_id: int
    qty_received: int

    model_config = {"from_attributes": True}


class ReceivingOut(BaseModel):
    recv_id: int
    recv_no: str
    po_id: int
    status: wire_enum(ReceivingStatus)
    received_at: datetime
    operator: str
    notes: str | None
    items: list[ReceivingItemOut]

    model_config = {"from_attributes": True}


class DefectIn(BaseModel):
    reason_code: wire_enum(DefectReason)
    qty: int


class InspectionResultIn(BaseModel):
    insp_item_id: int
    qty_passed: int
    defects: list[DefectIn] = []


class InspectionComplete(BaseModel):
    results: list[InspectionResultIn]


class InspectionItemOut(BaseModel):
    insp_item_id: int
    product_id: int
    qty_inspected: int
    qty_passed: int
    qty_failed: int

    model_config = {"from_attributes": True}


class InspectionOut(BaseModel):
    insp_id: int
    insp_no: str
    recv_id: int
    status: wire_enum(InspectionStatus)
    inspected_at: datetime | None
    inspector: str
    items: list[InspectionItemOut]

    model_config = {"from_attributes": True}
