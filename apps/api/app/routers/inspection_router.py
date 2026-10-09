"""质检单：列表/详情 + 开工/录入结果。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InspectionOrder
from app.schemas.receiving import InspectionComplete, InspectionOut
from app.services.inspection_service import (
    InspectionError,
    complete_inspection,
    start_inspection,
)
from app.services.inventory_ledger import LedgerError

router = APIRouter(prefix="/api/inspection", tags=["inspection"])


@router.get("", response_model=list[InspectionOut])
def list_inspection(db: Session = Depends(get_db)) -> list:
    return (
        db.query(InspectionOrder)
        .order_by(InspectionOrder.insp_id.desc())
        .all()
    )


@router.get("/{insp_id}", response_model=InspectionOut)
def get_inspection(
    insp_id: int, db: Session = Depends(get_db)
) -> InspectionOrder:
    insp = db.get(InspectionOrder, insp_id)
    if insp is None:
        raise HTTPException(status_code=404, detail=f"质检单不存在：{insp_id}")
    return insp


@router.post("/start/{recv_id}", response_model=InspectionOut)
def create_inspection(
    recv_id: int, db: Session = Depends(get_db)
) -> InspectionOrder:
    try:
        return start_inspection(db, recv_id)
    except InspectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{insp_id}/complete", response_model=InspectionOut)
def finish_inspection(
    insp_id: int,
    payload: InspectionComplete,
    db: Session = Depends(get_db),
) -> InspectionOrder:
    try:
        return complete_inspection(
            db,
            insp_id,
            [result.model_dump() for result in payload.results],
        )
    except InspectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LedgerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
