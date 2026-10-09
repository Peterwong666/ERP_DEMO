"""收货 + 质检流程测试（两种入库口径）。"""

from decimal import Decimal

import pytest
from app.models import (
    DefectRecord,
    InspectionItem,
    Inventory,
    InventoryTransaction,
    PurchaseOrder,
    ReceivingOrder,
    Supplier,
)
from app.models.enums import (
    DefectReason,
    InspectionStatus,
    POStatus,
    ReceivingStatus,
    SupplierStatus,
)
from app.schemas.products import POCreate, POLineIn, ProductCreate
from app.services import inventory_ledger
from app.services.inspection_service import (
    InspectionError,
    complete_inspection,
    start_inspection,
)
from app.services.po_service import create_draft, place_order
from app.services.product_service import create_product
from app.services.receiving_service import ReceivingError, receive_goods
from app.services.settings_service import update_values
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _set_caliber(db: Session, caliber: str) -> None:
    update_values(db, {"inbound_caliber": caliber})


def _placed_po(
    db: Session,
    lines: list[tuple[str, int]],
    supplier_code: str = "SUP-RCV-1",
) -> PurchaseOrder:
    supplier = Supplier(
        code=supplier_code,
        name="收货测试供应商",
        contact_person="c",
        email="r@example.com",
        phone="1",
        country="CN",
        lead_time_days=7,
        status=SupplierStatus.active,
    )
    db.add(supplier)
    db.flush()
    products = [
        create_product(
            db,
            ProductCreate(
                sku_code=sku,
                name=f"产品{sku}",
                category="electronics",
                standard_cost=Decimal("10.00"),
                weight_g=100,
                safety_stock=0,
                default_supplier_id=supplier.supplier_id,
            ),
        )
        for sku, _ in lines
    ]
    po = create_draft(
        db,
        POCreate(
            supplier_id=supplier.supplier_id,
            items=[
                POLineIn(
                    product_id=product.product_id,
                    qty_ordered=qty,
                    unit_price=Decimal("10.00"),
                )
                for product, (_, qty) in zip(products, lines, strict=True)
            ],
        ),
    )
    return place_order(db, po.po_id)


def _recv_lines(po: PurchaseOrder, qtys: list[int]) -> list[dict]:
    return [
        {"po_item_id": item.item_id, "qty_received": qty}
        for item, qty in zip(po.items, qtys, strict=True)
    ]


def _results(
    insp,
    passed: list[int],
    defects: list[list[tuple[DefectReason, int]]] | None = None,
) -> list[dict]:
    defect_rows = defects or []
    return [
        {
            "insp_item_id": item.insp_item_id,
            "qty_passed": qty_passed,
            "defects": [
                {"reason_code": reason, "qty": qty}
                for reason, qty in (
                    defect_rows[index] if index < len(defect_rows) else []
                )
            ],
        }
        for index, (item, qty_passed) in enumerate(
            zip(insp.items, passed, strict=True)
        )
    ]


def _stock_qty(db: Session, product_id: int, field: str) -> int:
    return int(
        db.execute(
            select(getattr(Inventory, field)).where(
                Inventory.product_id == product_id
            )
        ).scalar_one()
    )


# ---------- 收货 ----------

def test_full_receive_completes_po_and_creates_recv(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1001", 100)])

    recv = receive_goods(db, po.po_id, _recv_lines(po, [100]))

    assert recv.status == ReceivingStatus.pending_inspection
    assert recv.recv_no.startswith("RCV-")
    assert recv.items[0].qty_received == 100
    db.refresh(po)
    assert po.status == POStatus.received
    assert po.items[0].qty_received == 100


def test_partial_receive_then_remaining_completes_po(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1002", 100)])

    receive_goods(db, po.po_id, _recv_lines(po, [40]))
    db.refresh(po)
    assert po.status == POStatus.partial_received

    receive_goods(db, po.po_id, _recv_lines(po, [60]))
    db.refresh(po)
    assert po.status == POStatus.received
    assert po.items[0].qty_received == 100


def test_receive_over_remaining_rejected(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1003", 100)])

    with pytest.raises(ReceivingError):
        receive_goods(db, po.po_id, _recv_lines(po, [101]))


def test_receive_after_partial_cannot_exceed_remaining(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1004", 100)])
    receive_goods(db, po.po_id, _recv_lines(po, [60]))

    with pytest.raises(ReceivingError):
        receive_goods(db, po.po_id, _recv_lines(po, [41]))


def test_receive_rejects_draft_po(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1005", 10)])
    draft_po = create_draft(
        db,
        POCreate(
            supplier_id=po.supplier_id,
            items=[
                POLineIn(
                    product_id=po.items[0].product_id,
                    qty_ordered=5,
                    unit_price=Decimal("1"),
                )
            ],
        ),
    )

    with pytest.raises(ReceivingError):
        receive_goods(
            db,
            draft_po.po_id,
            [
                {
                    "po_item_id": draft_po.items[0].item_id,
                    "qty_received": 5,
                }
            ],
        )


def test_receive_unknown_po_raises(db: Session) -> None:
    _set_caliber(db, "inspection")
    with pytest.raises(LookupError):
        receive_goods(db, 999, [{"po_item_id": 1, "qty_received": 1}])


def test_receive_inspection_caliber_posts_to_pending(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1006", 100)])

    receive_goods(db, po.po_id, _recv_lines(po, [100]))

    product_id = po.items[0].product_id
    assert _stock_qty(db, product_id, "qty_pending") == 100
    assert _stock_qty(db, product_id, "qty_available") == 0


def test_receive_receiving_caliber_posts_to_available(db: Session) -> None:
    _set_caliber(db, "receiving")
    po = _placed_po(db, [("EC-1007", 100)])

    receive_goods(db, po.po_id, _recv_lines(po, [100]))

    product_id = po.items[0].product_id
    assert _stock_qty(db, product_id, "qty_available") == 100
    assert _stock_qty(db, product_id, "qty_pending") == 0


def test_receive_zero_or_negative_qty_rejected(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1008", 100)])

    with pytest.raises(ReceivingError):
        receive_goods(db, po.po_id, _recv_lines(po, [0]))


# ---------- 质检 ----------

def test_start_inspection_seeds_items_and_marks_recv(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1009", 100)])
    recv = receive_goods(db, po.po_id, _recv_lines(po, [100]))

    insp = start_inspection(db, recv.recv_id)

    assert insp.status == InspectionStatus.inspecting
    assert insp.items[0].qty_inspected == 100
    assert insp.items[0].qty_passed == 0
    db.refresh(recv)
    assert recv.status == ReceivingStatus.inspecting


def test_start_inspection_twice_rejected(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1010", 10)])
    recv = receive_goods(db, po.po_id, _recv_lines(po, [10]))
    start_inspection(db, recv.recv_id)

    with pytest.raises(InspectionError):
        start_inspection(db, recv.recv_id)


def test_start_inspection_unknown_recv_raises(db: Session) -> None:
    with pytest.raises(LookupError):
        start_inspection(db, 999)


def test_complete_all_passed_moves_pending_to_available(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1011", 100)])
    recv = receive_goods(db, po.po_id, _recv_lines(po, [100]))
    insp = start_inspection(db, recv.recv_id)

    completed = complete_inspection(db, insp.insp_id, _results(insp, [100]))

    assert completed.status == InspectionStatus.completed
    assert completed.inspected_at is not None
    item = completed.items[0]
    assert item.qty_passed == 100
    assert item.qty_failed == 0
    product_id = po.items[0].product_id
    assert _stock_qty(db, product_id, "qty_pending") == 0
    assert _stock_qty(db, product_id, "qty_available") == 100
    db.refresh(recv)
    assert recv.status == ReceivingStatus.completed


def test_complete_with_defects_moves_stock_and_records(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1012", 100)])
    recv = receive_goods(db, po.po_id, _recv_lines(po, [100]))
    insp = start_inspection(db, recv.recv_id)
    defects = [(DefectReason.scratch, 20), (DefectReason.functional, 10)]

    complete_inspection(db, insp.insp_id, _results(insp, [70], [defects]))

    product_id = po.items[0].product_id
    assert _stock_qty(db, product_id, "qty_pending") == 0
    assert _stock_qty(db, product_id, "qty_available") == 70
    assert _stock_qty(db, product_id, "qty_defective") == 30
    records = (
        db.query(DefectRecord)
        .join(DefectRecord.inspection_item)
        .filter(InspectionItem.insp_id == insp.insp_id)
        .all()
    )
    assert sorted(record.qty for record in records) == [10, 20]


def test_complete_defect_sum_mismatch_rejected(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1013", 100)])
    recv = receive_goods(db, po.po_id, _recv_lines(po, [100]))
    insp = start_inspection(db, recv.recv_id)
    results = _results(insp, [70], [[(DefectReason.scratch, 20)]])

    with pytest.raises(InspectionError):
        complete_inspection(db, insp.insp_id, results)


def test_complete_passed_exceeds_inspected_rejected(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1014", 100)])
    recv = receive_goods(db, po.po_id, _recv_lines(po, [100]))
    insp = start_inspection(db, recv.recv_id)

    with pytest.raises(InspectionError):
        complete_inspection(db, insp.insp_id, _results(insp, [101]))


def test_complete_receiving_caliber_moves_failed_from_available(
    db: Session,
) -> None:
    _set_caliber(db, "receiving")
    po = _placed_po(db, [("EC-1015", 100)])
    recv = receive_goods(db, po.po_id, _recv_lines(po, [100]))
    insp = start_inspection(db, recv.recv_id)

    complete_inspection(
        db,
        insp.insp_id,
        _results(insp, [70], [[(DefectReason.scratch, 30)]]),
    )

    product_id = po.items[0].product_id
    assert _stock_qty(db, product_id, "qty_available") == 70
    assert _stock_qty(db, product_id, "qty_defective") == 30
    assert _stock_qty(db, product_id, "qty_pending") == 0


def test_complete_non_inspecting_order_rejected(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1016", 10)])
    recv = receive_goods(db, po.po_id, _recv_lines(po, [10]))
    insp = start_inspection(db, recv.recv_id)
    complete_inspection(db, insp.insp_id, _results(insp, [10]))

    with pytest.raises(InspectionError):
        complete_inspection(db, insp.insp_id, _results(insp, [10]))


def test_full_flow_balance_equals_transactions(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-1017", 100), ("EC-1018", 50)])
    receive_goods(db, po.po_id, _recv_lines(po, [60, 50]))
    receive_goods(db, po.po_id, _recv_lines(po, [40, 0]))

    recv_orders = (
        db.query(ReceivingOrder).order_by(ReceivingOrder.recv_id).all()
    )
    insp1 = start_inspection(db, recv_orders[0].recv_id)
    complete_inspection(
        db,
        insp1.insp_id,
        _results(
            insp1,
            [50, 50],
            [[(DefectReason.scratch, 10)], []],
        ),
    )
    insp2 = start_inspection(db, recv_orders[1].recv_id)
    complete_inspection(db, insp2.insp_id, _results(insp2, [40]))

    assert inventory_ledger.find_reconciliation_mismatches(db) == []
    txn_count = db.execute(
        select(func.count()).select_from(InventoryTransaction)
    ).scalar_one()
    assert txn_count > 0


# ---------- HTTP ----------

def test_receive_and_inspect_full_http_flow(client, db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-2001", 100)])

    response = client.post(
        f"/api/receiving/po/{po.po_id}",
        json={
            "lines": [
                {"po_item_id": po.items[0].item_id, "qty_received": 100}
            ]
        },
    )
    assert response.status_code == 200
    recv_body = response.json()
    recv_id = recv_body["recv_id"]
    assert recv_body["status"] == "pending_inspection"

    started = client.post(f"/api/inspection/start/{recv_id}")
    assert started.status_code == 200
    insp_body = started.json()
    insp_id = insp_body["insp_id"]
    insp_item_id = insp_body["items"][0]["insp_item_id"]

    completed = client.post(
        f"/api/inspection/{insp_id}/complete",
        json={
            "results": [
                {
                    "insp_item_id": insp_item_id,
                    "qty_passed": 70,
                    "defects": [
                        {"reason_code": "scratch", "qty": 30}
                    ],
                }
            ]
        },
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"


def test_receive_http_over_remaining_returns_400(
    client, db: Session
) -> None:
    po = _placed_po(db, [("EC-2002", 10)])

    response = client.post(
        f"/api/receiving/po/{po.po_id}",
        json={
            "lines": [
                {"po_item_id": po.items[0].item_id, "qty_received": 11}
            ]
        },
    )
    assert response.status_code == 400


def test_start_inspection_http_unknown_recv_returns_404(client) -> None:
    response = client.post("/api/inspection/start/999")
    assert response.status_code == 404


def test_complete_with_duplicate_insp_item_rejected(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-2003", 10), ("EC-2004", 10)])
    receive_goods(db, po.po_id, _recv_lines(po, [10, 10]))
    recv = db.query(ReceivingOrder).one()
    insp = start_inspection(db, recv.recv_id)
    item_id = insp.items[0].insp_item_id
    duplicate_results = [
        {"insp_item_id": item_id, "qty_passed": 10, "defects": []},
        {"insp_item_id": item_id, "qty_passed": 10, "defects": []},
    ]

    with pytest.raises(InspectionError):
        complete_inspection(db, insp.insp_id, duplicate_results)


def test_receive_duplicate_po_item_rejected(db: Session) -> None:
    _set_caliber(db, "inspection")
    po = _placed_po(db, [("EC-2005", 100)])
    item_id = po.items[0].item_id
    duplicate_lines = [
        {"po_item_id": item_id, "qty_received": 60},
        {"po_item_id": item_id, "qty_received": 60},
    ]

    with pytest.raises(ReceivingError):
        receive_goods(db, po.po_id, duplicate_lines)


def test_receive_http_ledger_error_returns_409(
    client, db: Session, monkeypatch
) -> None:
    po = _placed_po(db, [("EC-2006", 10)])

    def _raise_ledger_error(*args, **kwargs):
        raise inventory_ledger.LedgerError("该 SKU 正在被并发过账")

    import app.routers.receiving_router as module

    monkeypatch.setattr(module, "receive_goods", _raise_ledger_error)

    response = client.post(
        f"/api/receiving/po/{po.po_id}",
        json={
            "lines": [
                {"po_item_id": po.items[0].item_id, "qty_received": 10}
            ]
        },
    )
    assert response.status_code == 409
