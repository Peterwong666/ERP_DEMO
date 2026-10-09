import pytest
from app.models import SystemSetting
from app.services.settings_service import (
    DEFAULT_SETTINGS,
    SettingValidationError,
    get_setting,
    reset_defaults,
    seed_defaults,
    update_values,
)
from sqlalchemy.orm import Session


def test_seed_defaults_inserts_five_settings(db: Session) -> None:
    # Arrange & Act
    seed_defaults(db)

    # Assert
    rows = db.query(SystemSetting).all()
    assert len(rows) == len(DEFAULT_SETTINGS)
    assert {row.key for row in rows} == {item.key for item in DEFAULT_SETTINGS}


def test_seed_defaults_is_idempotent(db: Session) -> None:
    # Arrange & Act
    seed_defaults(db)
    seed_defaults(db)

    # Assert
    assert db.query(SystemSetting).count() == len(DEFAULT_SETTINGS)


def test_get_setting_returns_typed_values(db: Session) -> None:
    # Arrange
    seed_defaults(db)

    # Act & Assert
    assert get_setting(db, "low_stock_days_threshold") == 14
    assert get_setting(db, "qc_pass_rate_target") == 95.0
    assert get_setting(db, "inbound_caliber") == "receiving"


def test_update_values_changes_setting(db: Session) -> None:
    # Arrange
    seed_defaults(db)

    # Act
    update_values(db, {"low_stock_days_threshold": "21"})

    # Assert
    assert get_setting(db, "low_stock_days_threshold") == 21


def test_update_values_rejects_unknown_key(db: Session) -> None:
    # Arrange
    seed_defaults(db)

    # Act & Assert
    with pytest.raises(SettingValidationError):
        update_values(db, {"unknown_key": "1"})


@pytest.mark.parametrize("bad_value", ["abc", "-1"])
def test_update_values_rejects_bad_int(db: Session, bad_value: str) -> None:
    # Arrange
    seed_defaults(db)

    # Act & Assert
    with pytest.raises(SettingValidationError):
        update_values(db, {"low_stock_days_threshold": bad_value})


def test_update_values_rejects_bad_float(db: Session) -> None:
    # Arrange
    seed_defaults(db)

    # Act & Assert
    with pytest.raises(SettingValidationError):
        update_values(db, {"qc_pass_rate_target": "not-a-number"})


def test_update_values_rejects_bad_enum_choice(db: Session) -> None:
    # Arrange
    seed_defaults(db)

    # Act & Assert
    with pytest.raises(SettingValidationError):
        update_values(db, {"inbound_caliber": "shipping"})


def test_reset_defaults_restores_modified_values(db: Session) -> None:
    # Arrange
    seed_defaults(db)
    update_values(db, {"urgency_emergency_days": "5"})

    # Act
    reset_defaults(db)

    # Assert
    assert get_setting(db, "urgency_emergency_days") == 10
    assert db.query(SystemSetting).count() == len(DEFAULT_SETTINGS)
