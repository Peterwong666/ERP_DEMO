"""供应商：只读列表（供下拉选择）。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Supplier
from app.models.enums import SupplierStatus
from app.schemas.enum_types import wire_enum


class SupplierOut(BaseModel):
    supplier_id: int
    code: str
    name: str
    lead_time_days: int
    status: wire_enum(SupplierStatus)

    model_config = {"from_attributes": True}


router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierOut])
def get_suppliers(db: Session = Depends(get_db)) -> list:
    return db.query(Supplier).order_by(Supplier.code).all()
