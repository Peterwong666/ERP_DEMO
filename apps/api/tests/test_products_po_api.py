"""产品 / 采购单 HTTP 层测试：状态码与错误翻译。"""

from app.models import Supplier
from app.models.enums import SupplierStatus
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _supplier(db: Session, code: str = "SUP-API-1") -> Supplier:
    supplier = Supplier(
        code=code,
        name="接口测试供应商",
        contact_person="联系人",
        email="api@example.com",
        phone="13800000000",
        country="中国",
        lead_time_days=7,
        status=SupplierStatus.active,
    )
    db.add(supplier)
    db.flush()
    return supplier


def _product_payload(supplier_id: int, **overrides) -> dict:
    payload = {
        "sku_code": "TEST-001",
        "name": "接口测试产品",
        "category": "electronics",
        "standard_cost": "10.00",
        "weight_g": 200,
        "safety_stock": 5,
        "default_supplier_id": supplier_id,
    }
    payload.update(overrides)
    return payload


def test_create_product_returns_201_with_defaults(
    client: TestClient, db: Session
) -> None:
    supplier = _supplier(db)

    response = client.post(
        "/api/products", json=_product_payload(supplier.supplier_id)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["sku_code"] == "TEST-001"
    assert body["status"] == "on_sale"
    assert body["unit"] == "件"


def test_list_products_filters_by_category_query(
    client: TestClient, db: Session
) -> None:
    supplier = _supplier(db)
    client.post("/api/products", json=_product_payload(supplier.supplier_id))

    response = client.get("/api/products", params={"category": "bags"})

    assert response.status_code == 200
    assert response.json() == []


def test_get_unknown_product_returns_404(client: TestClient) -> None:
    response = client.get("/api/products/999")

    assert response.status_code == 404


def test_patch_product_returns_updated_fields(
    client: TestClient, db: Session
) -> None:
    supplier = _supplier(db)
    product_id = client.post(
        "/api/products", json=_product_payload(supplier.supplier_id)
    ).json()["product_id"]

    response = client.patch(
        f"/api/products/{product_id}", json={"name": "改名后"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "改名后"


def test_change_status_toggles_product(
    client: TestClient, db: Session
) -> None:
    supplier = _supplier(db)
    product_id = client.post(
        "/api/products", json=_product_payload(supplier.supplier_id)
    ).json()["product_id"]

    response = client.post(
        f"/api/products/{product_id}/status",
        json={"status": "discontinued"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "discontinued"


def test_create_po_and_place_order_flow(
    client: TestClient, db: Session
) -> None:
    supplier = _supplier(db)
    product_id = client.post(
        "/api/products", json=_product_payload(supplier.supplier_id)
    ).json()["product_id"]

    create_response = client.post(
        "/api/purchase-orders",
        json={
            "supplier_id": supplier.supplier_id,
            "items": [
                {
                    "product_id": product_id,
                    "qty_ordered": 100,
                    "unit_price": "10.00",
                }
            ],
        },
    )
    assert create_response.status_code == 201
    po = create_response.json()
    assert po["status"] == "draft"
    assert po["total_amount"] == "1000.00"

    place_response = client.post(f"/api/purchase-orders/{po['po_id']}/place")
    assert place_response.status_code == 200
    assert place_response.json()["status"] == "ordered"


def test_create_po_empty_lines_returns_400(
    client: TestClient, db: Session
) -> None:
    supplier = _supplier(db)

    response = client.post(
        "/api/purchase-orders",
        json={"supplier_id": supplier.supplier_id, "items": []},
    )

    assert response.status_code == 400


def test_create_po_unknown_supplier_returns_404(
    client: TestClient, db: Session
) -> None:
    supplier = _supplier(db)
    product_id = client.post(
        "/api/products", json=_product_payload(supplier.supplier_id)
    ).json()["product_id"]

    response = client.post(
        "/api/purchase-orders",
        json={
            "supplier_id": 999,
            "items": [
                {
                    "product_id": product_id,
                    "qty_ordered": 1,
                    "unit_price": "1.00",
                }
            ],
        },
    )

    assert response.status_code == 404


def test_list_suppliers_returns_seeded_rows(
    client: TestClient, db: Session
) -> None:
    _supplier(db)

    response = client.get("/api/suppliers")

    assert response.status_code == 200
    suppliers = response.json()
    assert len(suppliers) == 1
    assert suppliers[0]["code"] == "SUP-API-1"
    assert suppliers[0]["status"] == "active"


def test_place_order_twice_returns_400(
    client: TestClient, db: Session
) -> None:
    supplier = _supplier(db)
    product_id = client.post(
        "/api/products", json=_product_payload(supplier.supplier_id)
    ).json()["product_id"]
    po_id = client.post(
        "/api/purchase-orders",
        json={
            "supplier_id": supplier.supplier_id,
            "items": [
                {
                    "product_id": product_id,
                    "qty_ordered": 10,
                    "unit_price": "10.00",
                }
            ],
        },
    ).json()["po_id"]
    client.post(f"/api/purchase-orders/{po_id}/place")

    response = client.post(f"/api/purchase-orders/{po_id}/place")

    assert response.status_code == 400
