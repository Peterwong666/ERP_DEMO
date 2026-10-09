"""产品 CRUD 与上下架状态切换。"""

from sqlalchemy.orm import Session

from app.models import Product
from app.models.enums import ProductCategory, ProductStatus
from app.schemas.products import ProductCreate, ProductUpdate


def create_product(db: Session, payload: ProductCreate) -> Product:
    product = Product(status=ProductStatus.on_sale, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def list_products(
    db: Session, category: ProductCategory | None = None
) -> list[Product]:
    query = db.query(Product)
    if category is not None:
        query = query.filter(Product.category == category)
    return query.order_by(Product.sku_code).all()


def get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise LookupError(f"产品不存在：{product_id}")
    return product


def update_product(db: Session, product_id: int, payload: ProductUpdate) -> Product:
    product = get_product(db, product_id)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field_name, value)
    db.commit()
    db.refresh(product)
    return product


def change_status(
    db: Session, product_id: int, status: ProductStatus
) -> Product:
    product = get_product(db, product_id)
    product.status = status
    db.commit()
    db.refresh(product)
    return product
