"""产品：列表/详情/新建/编辑/上下架。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import ProductCategory
from app.schemas.enum_types import wire_enum
from app.schemas.products import (
    ProductCreate,
    ProductOut,
    ProductStatusUpdate,
    ProductUpdate,
)
from app.services.product_service import (
    change_status,
    create_product,
    get_product,
    list_products,
    update_product,
)

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def get_products(
    category: wire_enum(ProductCategory) | None = None,
    db: Session = Depends(get_db),
) -> list:
    return list_products(db, category=category)


@router.get("/{product_id}", response_model=ProductOut)
def get_one_product(
    product_id: int, db: Session = Depends(get_db)
) -> ProductOut:
    try:
        return get_product(db, product_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("", response_model=ProductOut, status_code=201)
def post_product(
    payload: ProductCreate, db: Session = Depends(get_db)
) -> ProductOut:
    return create_product(db, payload)


@router.patch("/{product_id}", response_model=ProductOut)
def patch_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
) -> ProductOut:
    try:
        return update_product(db, product_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{product_id}/status", response_model=ProductOut)
def post_product_status(
    product_id: int,
    payload: ProductStatusUpdate,
    db: Session = Depends(get_db),
) -> ProductOut:
    try:
        return change_status(db, product_id, payload.status)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
