from fastapi.testclient import TestClient


def test_get_settings_returns_five_defaults(client: TestClient) -> None:
    # Act
    response = client.get("/api/settings")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    by_key = {item["key"]: item for item in data}
    assert by_key["low_stock_days_threshold"]["value"] == "14"
    assert by_key["inbound_caliber"]["value"] == "receiving"


def test_put_settings_updates_value(client: TestClient) -> None:
    # Arrange
    updated = {"values": {"low_stock_days_threshold": "21"}}

    # Act
    response = client.put("/api/settings", json=updated)

    # Assert
    assert response.status_code == 200
    by_key = {item["key"]: item for item in response.json()}
    assert by_key["low_stock_days_threshold"]["value"] == "21"


def test_put_settings_rejects_invalid_value(client: TestClient) -> None:
    # Act
    response = client.put(
        "/api/settings", json={"values": {"low_stock_days_threshold": "abc"}}
    )

    # Assert
    assert response.status_code == 400


def test_put_settings_rejects_unknown_key(client: TestClient) -> None:
    # Act
    response = client.put("/api/settings", json={"values": {"nope": "1"}})

    # Assert
    assert response.status_code == 400


def test_reset_settings_restores_defaults(client: TestClient) -> None:
    # Arrange
    client.put("/api/settings", json={"values": {"urgency_suggestion_days": "30"}})

    # Act
    response = client.post("/api/settings/reset")

    # Assert
    assert response.status_code == 200
    by_key = {item["key"]: item for item in response.json()}
    assert by_key["urgency_suggestion_days"]["value"] == "21"
