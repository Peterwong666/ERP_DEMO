"""种子数据关键路径：8 项数字、库存对账、可追溯、幂等、口径切换。"""

from app.models import Base, Inventory, InventoryTransaction
from app.models.enums import StockType
from app.seeds.builder import ANCHOR, seed_all
from app.seeds.check import EXPECTED
from app.services.metrics_service import compute_metrics
from app.services.settings_service import update_values
from sqlalchemy import func, select


def _check_metrics(db) -> None:
    metrics = compute_metrics(db, anchor=ANCHOR)
    # 真值表与 make check 共享（app.seeds.check.EXPECTED），避免双份维护
    for field_name, expected in EXPECTED:
        assert getattr(metrics, field_name) == expected


def test_seed_hits_eight_dashboard_numbers(db) -> None:
    seed_all(db)
    _check_metrics(db)


def test_inventory_balance_equals_transactions(db) -> None:
    seed_all(db)
    for inventory in db.execute(select(Inventory)).scalars().all():
        for stock_type in StockType:
            txn_sum = db.execute(
                select(func.coalesce(func.sum(InventoryTransaction.change_qty), 0)).where(
                    InventoryTransaction.product_id == inventory.product_id,
                    InventoryTransaction.stock_type == stock_type,
                )
            ).scalar_one()
            assert txn_sum == getattr(inventory, f"qty_{stock_type.name}")


def test_every_transaction_traces_to_document(db) -> None:
    seed_all(db)
    transactions = db.execute(select(InventoryTransaction)).scalars().all()
    assert len(transactions) > 0
    assert all(txn.ref_doc_type and txn.ref_doc_no for txn in transactions)


def _snapshot(db) -> dict[str, int]:
    return {
        table.name: int(
            db.execute(select(func.count()).select_from(table)).scalar_one()
        )
        for table in Base.metadata.sorted_tables
    }


def test_seed_is_idempotent(db) -> None:
    bind = db.bind
    seed_all(db)
    counts_after_first = _snapshot(db)
    metrics_after_first = compute_metrics(db, anchor=ANCHOR)

    Base.metadata.drop_all(bind)
    Base.metadata.create_all(bind)
    seed_all(db)

    assert _snapshot(db) == counts_after_first
    assert compute_metrics(db, anchor=ANCHOR) == metrics_after_first


def test_defect_distribution_matches_design(db) -> None:
    seed_all(db)
    metrics = compute_metrics(db, anchor=ANCHOR)
    shares = {share.reason_code: share.qty for share in metrics.defect_shares}
    assert shares == {
        "scratch": 38,
        "functional": 22,
        "packaging": 18,
        "dimension": 12,
        "label": 7,
        "other": 5,
    }


def test_inbound_caliber_switch_to_inspection(db) -> None:
    seed_all(db)
    update_values(db, {"inbound_caliber": "inspection"})
    metrics = compute_metrics(db, anchor=ANCHOR)
    assert metrics.inbound_today_qty == metrics.qc_passed_today == 136


def test_dashboard_endpoint_matches_check(db, client) -> None:
    seed_all(db)
    response = client.get("/api/dashboard", params={"anchor": ANCHOR.isoformat()})
    assert response.status_code == 200
    payload = response.json()
    assert payload["open_po_count"] == 4
    assert payload["inbound_today_qty"] == 1284
    assert payload["qc_pass_rate"] == 57.1
    assert payload["inbound_last_7d"][-1] == 1284
    assert len(payload["defect_shares"]) == 6
    # 锚点日期随响应返回，前端 X 轴标签必须以后端日期为准
    assert payload["anchor_date"] == ANCHOR.isoformat()


def test_dashboard_endpoint_echoes_custom_anchor(db, client) -> None:
    seed_all(db)
    custom_anchor = "2026-09-30"
    response = client.get("/api/dashboard", params={"anchor": custom_anchor})
    assert response.status_code == 200
    assert response.json()["anchor_date"] == custom_anchor
