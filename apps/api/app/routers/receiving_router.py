"""收货单：列表/详情 + 对采购单收货。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ReceivingOrder
from app.schemas.receiving import ReceivingCreate, ReceivingOut
from app.services.inventory_ledger import LedgerError
from app.services.receiving_service import ReceivingError, receive_goods

router = APIRouter(prefix="/api/receiving", tags=["receiving"])


@router.get("", response_model=list[ReceivingOut])
def list_receiving(db: Session = Depends(get_db)) -> list:
    return (
        db.query(ReceivingOrder)
        .order_by(ReceivingOrder.recv_id.desc())
        .all()
    )


@router.get("/{recv_id}", response_model=ReceivingOut)
def get_receiving(recv_id: int, db: Session = Depends(get_db)) -> ReceivingOrder:
    recv = db.get(ReceivingOrder, recv_id)
    if recv is None:
        raise HTTPException(status_code=404, detail=f"收货单不存在：{recv_id}")
    return recv


@router.post("/po/{po_id}", response_model=ReceivingOut)
def create_receiving(
    po_id: int,
    payload: ReceivingCreate,
    db: Session = Depends(get_db),
) -> ReceivingOrder:
    try:
        return receive_goods(
            db,
            po_id,
            [line.model_dump() for line in payload.lines],
        )
    except ReceivingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LedgerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
