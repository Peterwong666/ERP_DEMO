"""确定性种子数据生成（无随机数，锚点 T = 2026-10-09）。

故事线：
- 过去 6 天每天一批趋势入库（收货→质检→出库，净额为 0）；
- 10-07/10-08 的 3 批到货在今日完成质检（238/136/102）；
- 今日 5 批到货待质检，合计 1,284 件；
- 4 张部分收货的在途 PO；
- 近 30 天销量按周内固定波形生成；
- 期初余额作为最后一笔倒挤，保证库存余额精确命中目标。
"""

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import (
    DailySales,
    DefectRecord,
    InspectionItem,
    InspectionOrder,
    Inventory,
    InventoryTransaction,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    ReceivingItem,
    ReceivingOrder,
    Supplier,
)
from app.models.enums import (
    DefectReason,
    InspectionStatus,
    POStatus,
    ProductCategory,
    ProductStatus,
    ReceivingStatus,
    StockType,
    SupplierStatus,
    TxnType,
)
from app.services.settings_service import seed_defaults

ANCHOR = date(2026, 10, 9)
DATA_DIR = Path(__file__).parent / "data"

# 周内销量系数：周一..周日
WEEKDAY_MULT = (1.0, 0.9, 1.1, 1.0, 1.2, 1.3, 1.2)

OPERATOR = "系统"


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute))


def _load_json(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8") as fp:
        return json.load(fp)


# ---------- 单据构造助手 ----------

def _make_po(
    db: Session,
    po_no: str,
    supplier: Supplier,
    status: POStatus,
    order_day: date,
    lines: list[tuple[Product, int, int]],
) -> tuple[PurchaseOrder, list[PurchaseOrderItem]]:
    po = PurchaseOrder(
        po_no=po_no,
        supplier_id=supplier.supplier_id,
        status=status,
        total_amount=sum(
            product.standard_cost * qty_ordered for product, qty_ordered, _ in lines
        ),
        order_date=order_day,
        expected_date=order_day + timedelta(days=supplier.lead_time_days),
        created_by=OPERATOR,
    )
    db.add(po)
    db.flush()
    items = [
        PurchaseOrderItem(
            po_id=po.po_id,
            product_id=product.product_id,
            qty_ordered=qty_ordered,
            qty_received=qty_received,
            unit_price=product.standard_cost,
        )
        for product, qty_ordered, qty_received in lines
    ]
    db.add_all(items)
    db.flush()
    return po, items


def _receive(
    db: Session,
    recv_no: str,
    po: PurchaseOrder,
    pairs: list[tuple[PurchaseOrderItem, int]],
    when: datetime,
    status: ReceivingStatus,
) -> tuple[ReceivingOrder, list[ReceivingItem]]:
    recv = ReceivingOrder(
        recv_no=recv_no,
        po_id=po.po_id,
        status=status,
        received_at=when,
        operator="仓管员",
        created_by=OPERATOR,
    )
    db.add(recv)
    db.flush()
    items = [
        ReceivingItem(
            recv_id=recv.recv_id,
            po_item_id=po_item.item_id,
            product_id=po_item.product_id,
            qty_received=qty,
        )
        for po_item, qty in pairs
    ]
    db.add_all(items)
    db.flush()
    return recv, items


def _inspect(
    db: Session,
    insp_no: str,
    recv: ReceivingOrder,
    rows: list[tuple[Product, int, int]],
    when: datetime,
    status: InspectionStatus,
) -> tuple[InspectionOrder, list[InspectionItem]]:
    insp = InspectionOrder(
        insp_no=insp_no,
        recv_id=recv.recv_id,
        status=status,
        inspected_at=when if status == InspectionStatus.completed else None,
        inspector="质检员",
        created_by=OPERATOR,
    )
    db.add(insp)
    db.flush()
    items = [
        InspectionItem(
            insp_id=insp.insp_id,
            product_id=product.product_id,
            qty_inspected=qty_inspected,
            qty_passed=qty_passed,
            qty_failed=qty_inspected - qty_passed,
        )
        for product, qty_inspected, qty_passed in rows
    ]
    db.add_all(items)
    db.flush()
    return insp, items


def _add_defects(
    db: Session, insp_item: InspectionItem, reasons: list[tuple[DefectReason, int]]
) -> None:
    db.add_all(
        DefectRecord(
            insp_item_id=insp_item.insp_item_id,
            reason_code=reason,
            qty=qty,
        )
        for reason, qty in reasons
    )


# ---------- 库存流水 ----------

def _txn(
    product: Product,
    qty: int,
    stock_type: StockType,
    txn_type: TxnType,
    ref_doc_type: str,
    ref_doc_no: str,
    when: datetime,
    reason: str = "",
) -> InventoryTransaction:
    return InventoryTransaction(
        product_id=product.product_id,
        change_qty=qty,
        stock_type=stock_type,
        txn_type=txn_type,
        ref_doc_type=ref_doc_type,
        ref_doc_no=ref_doc_no,
        reason=reason,
        operator=OPERATOR,
        created_at=when,
    )


# ---------- 主流程 ----------

def seed_all(db: Session) -> None:
    products_raw = _load_json("products.json")
    suppliers_raw = _load_json("suppliers.json")

    suppliers: dict[str, Supplier] = {}
    for row in suppliers_raw:
        supplier = Supplier(
            code=row["code"],
            name=row["name"],
            contact_person=row["contact_person"],
            email=row["email"],
            phone=row["phone"],
            country=row["country"],
            lead_time_days=row["lead_time_days"],
            status=SupplierStatus[row["status"]],
        )
        db.add(supplier)
        suppliers[row["code"]] = supplier
    db.flush()

    products: dict[str, Product] = {}
    for row in products_raw:
        product = Product(
            sku_code=row["sku_code"],
            name=row["name"],
            category=ProductCategory[row["category"]],
            status=ProductStatus.on_sale,
            unit=row["unit"],
            standard_cost=Decimal(row["standard_cost"]),
            weight_g=row["weight_g"],
            safety_stock=row["safety_stock"],
            default_supplier_id=suppliers[row["supplier_code"]].supplier_id,
            barcode=row["barcode"],
            description=row["description"],
        )
        db.add(product)
        products[row["sku_code"]] = product
    db.flush()

    # product_id → SKU 反向索引（供流水构造反查）
    sku_by_product_id = {product.product_id: sku for sku, product in products.items()}

    transactions: list[InventoryTransaction] = []

    # -- 趋势历史：每天 PO→收货→质检→出库（净额 0） --
    trend_days: list[tuple[date, list[tuple[str, int]]]] = [
        (date(2026, 10, 3), [("EC-0006", 300), ("EC-0012", 280), ("EC-0018", 240)]),
        (date(2026, 10, 4), [("EC-0016", 360), ("EC-0017", 320), ("EC-0019", 280)]),
        (date(2026, 10, 5), [("BG-0001", 260), ("BG-0003", 240), ("BG-0005", 206)]),
        (date(2026, 10, 6), [("BG-0006", 400), ("BG-0007", 380), ("BG-0008", 320)]),
        (date(2026, 10, 7), [("HM-0002", 360), ("HM-0004", 340), ("HM-0006", 340)]),
        (date(2026, 10, 8), [("HM-0007", 300), ("HM-0008", 300), ("AP-0002", 300)]),
    ]
    for day, sku_qtys in trend_days:
        tag = day.strftime("%Y%m%d")
        lines = [(products[sku], qty, qty) for sku, qty in sku_qtys]
        po, po_items = _make_po(
            db, f"PO-{tag}-T", suppliers["SUP-009"], POStatus.received, day, lines
        )
        recv, _ = _receive(
            db, f"RCV-{tag}-T", po,
            list(zip(po_items, [q for _, q in sku_qtys], strict=True)),
            _at(day, 9), ReceivingStatus.completed,
        )
        _inspect(
            db,
            f"INSP-{tag}-T",
            recv,
            [(products[sku], qty, qty) for sku, qty in sku_qtys],
            _at(day, 15),
            InspectionStatus.completed,
        )
        for po_item in po_items:
            product = products[sku_by_product_id[po_item.product_id]]
            qty = next(q for sku, q in sku_qtys if sku == product.sku_code)
            # 注：SO 为叙事占位——销售单未建模，本种子中所有 ref_doc_no="SO-*"
            # 的出库流水均无真实单据可 join
            transactions.extend(
                [
                    _txn(product, qty, StockType.pending, TxnType.recv_inbound,
                         "PO", po.po_no, _at(day, 9)),
                    _txn(product, -qty, StockType.pending, TxnType.qc_pass,
                         "RCV", recv.recv_no, _at(day, 15)),
                    _txn(product, qty, StockType.available, TxnType.qc_pass,
                         "INSP", f"INSP-{tag}-T", _at(day, 15)),
                    _txn(product, -qty, StockType.available, TxnType.adjust_outbound,
                         "SO", f"SO-{tag}", _at(day, 18)),
                ]
            )

    # -- 今日完成质检的 3 批历史到货 --
    qc_story = [
        (
            date(2026, 10, 7), "EC-0005", 100, 60,
            [(DefectReason.scratch, 18), (DefectReason.functional, 10),
             (DefectReason.packaging, 7), (DefectReason.dimension, 5)],
        ),
        (
            date(2026, 10, 8), "EC-0013", 80, 46,
            [(DefectReason.scratch, 12), (DefectReason.functional, 8),
             (DefectReason.packaging, 6), (DefectReason.dimension, 4),
             (DefectReason.label, 4)],
        ),
        (
            date(2026, 10, 8), "HM-0003", 58, 30,
            [(DefectReason.scratch, 8), (DefectReason.functional, 4),
             (DefectReason.packaging, 5), (DefectReason.dimension, 3),
             (DefectReason.label, 3), (DefectReason.other, 5)],
        ),
    ]
    for idx, (day, sku, total, passed, defects) in enumerate(qc_story, start=1):
        product = products[sku]
        tag = day.strftime("%Y%m%d")
        po, po_items = _make_po(
            db, f"PO-{tag}-H{idx}", suppliers["SUP-009"],
            POStatus.received, day, [(product, total, total)],
        )
        recv, _ = _receive(
            db, f"RCV-{tag}-H{idx}", po, [(po_items[0], total)],
            _at(day, 10), ReceivingStatus.completed,
        )
        _, insp_items = _inspect(
            db, f"INSP-20261009-H{idx}", recv, [(product, total, passed)],
            _at(ANCHOR, 10, idx * 15), InspectionStatus.completed,
        )
        _add_defects(db, insp_items[0], defects)
        failed = total - passed
        # 防守不变量：不良明细合计必须等于本批不合格数
        assert sum(qty for _, qty in defects) == failed
        transactions.extend(
            [
                _txn(product, total, StockType.pending, TxnType.recv_inbound,
                     "PO", po.po_no, _at(day, 10)),
                _txn(product, -passed, StockType.pending, TxnType.qc_pass,
                     "INSP", f"INSP-20261009-H{idx}",
                     _at(ANCHOR, 10, idx * 15)),
                _txn(product, passed, StockType.available, TxnType.qc_pass,
                     "INSP", f"INSP-20261009-H{idx}",
                     _at(ANCHOR, 10, idx * 15)),
                _txn(product, -failed, StockType.pending, TxnType.qc_fail,
                     "INSP", f"INSP-20261009-H{idx}",
                     _at(ANCHOR, 10, idx * 15)),
                _txn(product, failed, StockType.defective, TxnType.qc_fail,
                     "INSP", f"INSP-20261009-H{idx}",
                     _at(ANCHOR, 10, idx * 15)),
            ]
        )

    # -- 4 张在途 PO + 今日 5 批待质检到货（1,284 件） --
    today_tag = "20261009"
    open_po_specs: list[tuple[str, str, list[tuple[str, int, int]]]] = [
        ("PO-20261008-01", "SUP-002", [("EC-0008", 600, 300)]),
        ("PO-20261008-02", "SUP-009",
         [("EC-0020", 560, 280), ("EC-0003", 480, 240)]),
        ("PO-20261008-03", "SUP-004",
         [("EC-0015", 500, 250), ("HM-0008", 300, 0)]),
        ("PO-20261008-04", "SUP-001", [("EC-0011", 400, 214)]),
    ]
    recv_seq = 0
    for po_no, supplier_code, spec_lines in open_po_specs:
        lines = [
            (products[sku], qty_ordered, qty_received)
            for sku, qty_ordered, qty_received in spec_lines
        ]
        po, po_items = _make_po(
            db, po_no, suppliers[supplier_code], POStatus.partial_received,
            ANCHOR - timedelta(days=1), lines,
        )
        for po_item, (_, _, qty_received) in zip(
            po_items, spec_lines, strict=True
        ):
            if qty_received == 0:
                continue
            recv_seq += 1
            recv_status = (
                ReceivingStatus.inspecting
                if recv_seq == 5
                else ReceivingStatus.pending_inspection
            )
            recv, _ = _receive(
                db, f"RCV-{today_tag}-{recv_seq:02d}", po,
                [(po_item, qty_received)],
                _at(ANCHOR, 8, recv_seq * 10), recv_status,
            )
            product = products[sku_by_product_id[po_item.product_id]]
            transactions.append(
                _txn(product, qty_received, StockType.pending,
                     TxnType.recv_inbound, "PO", po.po_no,
                     _at(ANCHOR, 8, recv_seq * 10))
            )

    # -- 近 30 天销量 + 出库流水 --
    sales_start = ANCHOR - timedelta(days=30)
    for product in products.values():
        sales_avg = next(
            row["sales_avg"] for row in products_raw
            if row["sku_code"] == product.sku_code
        )
        if sales_avg == 0:
            continue
        for offset in range(30):
            day = sales_start + timedelta(days=offset)
            qty = round(sales_avg * WEEKDAY_MULT[day.weekday()])
            if qty == 0:
                continue
            db.add(DailySales(product_id=product.product_id, date=day, qty_sold=qty))
            transactions.append(
                _txn(product, -qty, StockType.available,
                     TxnType.adjust_outbound, "SO", f"SO-{day.isoformat()}",
                     _at(day, 18))
            )

    # -- 期初余额倒挤：保证每 SKU available 精确命中目标 --
    targets = {row["sku_code"]: row["target_available"] for row in products_raw}
    available_sum: dict[int, int] = {}
    for txn in transactions:
        if txn.stock_type == StockType.available:
            available_sum[txn.product_id] = (
                available_sum.get(txn.product_id, 0) + txn.change_qty
            )
    opening_day = sales_start - timedelta(days=1)
    for sku, target in targets.items():
        product = products[sku]
        opening = target - available_sum.get(product.product_id, 0)
        transactions.append(
            _txn(product, opening, StockType.available, TxnType.manual_adjust,
                 "OPENING", f"OPEN-{sku}", _at(opening_day, 0),
                 reason="期初余额导入")
        )

    db.add_all(transactions)
    db.flush()

    # -- Inventory 表按流水汇总物化 --
    balances: dict[int, dict[StockType, int]] = {}
    for txn in transactions:
        sku_balances = balances.setdefault(
            txn.product_id,
            {StockType.available: 0, StockType.pending: 0,
             StockType.defective: 0},
        )
        sku_balances[txn.stock_type] += txn.change_qty
    db.add_all(
        Inventory(
            product_id=product_id,
            qty_available=qty_balances[StockType.available],
            qty_pending=qty_balances[StockType.pending],
            qty_defective=qty_balances[StockType.defective],
            location="A-01",
        )
        for product_id, qty_balances in balances.items()
    )

    seed_defaults(db)
    db.commit()
