"""库存台账：余额列表、流水过滤、手工调整、对账、低库存。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.enums import StockType, TxnType
from app.schemas.inventory import (
    AdjustIn,
    BalanceOut,
    LowStockOut,
    ReconciliationOut,
    TransactionOut,
)
from app.services import inventory_ledger
from app.services.inventory_service import (
    InventoryValidationError,
    list_balances,
    manual_adjust,
    query_transactions,
)
from app.services.stock_analytics import find_low_stock

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def _resolve_enum(value: str, enum_cls: type, label: str):
    try:
        return enum_cls[value]
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"{label}取值无效：{value}") from exc


@router.get("", response_model=list[BalanceOut])
def get_balances(db: Session = Depends(get_db)) -> list:
    return list_balances(db)


@router.get("/transactions", response_model=list[TransactionOut])
def get_transactions(
    product_id: int | None = None,
    ref_doc_no: str | None = None,
    txn_type: str | None = None,
    stock_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
) -> list:
    try:
        return query_transactions(
            db,
            product_id=product_id,
            ref_doc_no=ref_doc_no,
            txn_type=(
                _resolve_enum(txn_type, TxnType, "流水类型") if txn_type else None
            ),
            stock_type=(
                _resolve_enum(stock_type, StockType, "库存类型")
                if stock_type
                else None
            ),
            date_from=date_from,
            date_to=date_to,
        )
    except InventoryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/adjust", response_model=TransactionOut)
def post_adjust(payload: AdjustIn, db: Session = Depends(get_db)):
    try:
        return manual_adjust(
            db, payload.product_id, payload.change_qty, payload.reason
        )
    except InventoryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except inventory_ledger.LedgerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/reconciliation", response_model=list[ReconciliationOut])
def get_reconciliation(db: Session = Depends(get_db)) -> list:
    return inventory_ledger.find_reconciliation_mismatches(db)


@router.get("/low-stock", response_model=list[LowStockOut])
def get_low_stock(db: Session = Depends(get_db)) -> list[LowStockOut]:
    return [
        LowStockOut(
            product_id=product.product_id,
            sku_code=product.sku_code,
            name=product.name,
            days_cover=days_cover,
            qty_available=qty_available,
            safety_stock=product.safety_stock,
        )
        for product, days_cover, qty_available in find_low_stock(
            db, settings.data_anchor_date
        )
    ]
