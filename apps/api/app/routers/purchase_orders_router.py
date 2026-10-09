"""采购单：列表/详情/建草稿/下单/取消。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.products import POCreate, POOut
from app.services.po_service import (
    POError,
    cancel_order,
    create_draft,
    get_purchase_order,
    list_purchase_orders,
    place_order,
)

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase-orders"])


@router.get("", response_model=list[POOut])
def get_purchase_orders(db: Session = Depends(get_db)) -> list:
    return list_purchase_orders(db)


@router.get("/{po_id}", response_model=POOut)
def get_one_purchase_order(
    po_id: int, db: Session = Depends(get_db)
) -> POOut:
    try:
        return get_purchase_order(db, po_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", response_model=POOut, status_code=201)
def post_purchase_order(
    payload: POCreate, db: Session = Depends(get_db)
) -> POOut:
    try:
        return create_draft(db, payload)
    except POError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{po_id}/place", response_model=POOut)
def post_place_order(po_id: int, db: Session = Depends(get_db)) -> POOut:
    try:
        return place_order(db, po_id)
    except POError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{po_id}/cancel", response_model=POOut)
def post_cancel_order(po_id: int, db: Session = Depends(get_db)) -> POOut:
    try:
        return cancel_order(db, po_id)
    except POError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
