"""make up 自动播种：空库才写种子，已有数据绝不覆盖。"""

from app.models import Base, Product
from app.seeds.builder import ANCHOR
from app.seeds.ensure_seed import ensure_seed
from app.services.metrics_service import compute_metrics
from sqlalchemy import func, select


def test_ensure_seed_populates_empty_db(db) -> None:
    assert ensure_seed(db) is True

    product_count = db.execute(
        select(func.count()).select_from(Product)
    ).scalar_one()
    assert product_count == 50

    metrics = compute_metrics(db, anchor=ANCHOR)
    assert metrics.available_sku_count == 50
    assert metrics.low_stock_count == 6


def test_ensure_seed_skips_when_data_exists(db) -> None:
    assert ensure_seed(db) is True

    snapshot = {
        table.name: int(
            db.execute(select(func.count()).select_from(table)).scalar_one()
        )
        for table in Base.metadata.sorted_tables
    }

    assert ensure_seed(db) is False

    after = {
        table.name: int(
            db.execute(select(func.count()).select_from(table)).scalar_one()
        )
        for table in Base.metadata.sorted_tables
    }
    assert after == snapshot
