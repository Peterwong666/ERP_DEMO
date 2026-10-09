"""make up：库为空时自动播种，已有数据则跳过（非破坏性）。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import Base, Product
from app.seeds.builder import seed_all


def ensure_seed(db: Session) -> bool:
    """空库写入种子数据并返回 True；已有商品时保持不动返回 False。"""
    product_count = db.execute(
        select(func.count()).select_from(Product)
    ).scalar_one()
    if product_count > 0:
        return False
    seed_all(db)
    return True


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if ensure_seed(db):
            print("数据库为空，已写入种子数据（锚点 2026-10-09）")
        else:
            print("检测到已有数据，跳过播种")
    finally:
        db.close()


if __name__ == "__main__":
    main()
