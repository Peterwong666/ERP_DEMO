from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import SystemSetting
from app.models.enums import SettingCategory, SettingValueType


class SettingValidationError(ValueError):
    pass


@dataclass(frozen=True)
class DefaultSetting:
    key: str
    value: str
    value_type: SettingValueType
    category: SettingCategory
    label: str
    description: str
    enum_choices: tuple[str, ...] = ()


DEFAULT_SETTINGS: tuple[DefaultSetting, ...] = (
    DefaultSetting(
        key="low_stock_days_threshold",
        value="14",
        value_type=SettingValueType.int,
        category=SettingCategory.stock_alert,
        label="低库存预警天数",
        description="可售天数低于该值触发低库存预警",
    ),
    DefaultSetting(
        key="urgency_emergency_days",
        value="10",
        value_type=SettingValueType.int,
        category=SettingCategory.replenishment,
        label="紧急补货阈值",
        description="可售天数 ≤ 此值判为「紧急」",
    ),
    DefaultSetting(
        key="urgency_suggestion_days",
        value="21",
        value_type=SettingValueType.int,
        category=SettingCategory.replenishment,
        label="建议补货阈值",
        description="可售天数 ≤ 此值判为「建议」",
    ),
    DefaultSetting(
        key="qc_pass_rate_target",
        value="95",
        value_type=SettingValueType.float,
        category=SettingCategory.qc,
        label="质检良率目标",
        description="良率(%)低于该目标则警示",
    ),
    DefaultSetting(
        key="inbound_caliber",
        value="receiving",
        value_type=SettingValueType.enum,
        category=SettingCategory.caliber,
        label="入库口径",
        description="receiving=收货入库；inspection=质检合格入库",
        enum_choices=("receiving", "inspection"),
    ),
)

SETTINGS_BY_KEY: dict[str, DefaultSetting] = {item.key: item for item in DEFAULT_SETTINGS}


def _insert_missing(db: Session) -> None:
    existing = {row.key for row in db.query(SystemSetting).all()}
    for item in DEFAULT_SETTINGS:
        if item.key in existing:
            continue
        db.add(
            SystemSetting(
                key=item.key,
                value=item.value,
                value_type=item.value_type,
                category=item.category,
                label=item.label,
                description=item.description,
            )
        )


def seed_defaults(db: Session) -> None:
    """Insert any missing default settings and commit. Never overwrites user values."""
    _insert_missing(db)
    db.commit()


def _ensure_defaults(db: Session) -> None:
    """Same fill without commit: read paths must not trigger a write."""
    _insert_missing(db)
    db.flush()


def list_settings(db: Session) -> list[SystemSetting]:
    _ensure_defaults(db)
    return db.query(SystemSetting).order_by(SystemSetting.setting_id).all()


def _convert(key: str, raw_value: str) -> int | float | str:
    spec = SETTINGS_BY_KEY.get(key)
    if spec is None:
        raise SettingValidationError(f"未知设置项：{key}")
    if spec.value_type is SettingValueType.int:
        try:
            value = int(raw_value)
        except ValueError as exc:
            raise SettingValidationError(f"{spec.label}必须为整数") from exc
        if value < 0:
            raise SettingValidationError(f"{spec.label}不可为负数")
        return value
    if spec.value_type is SettingValueType.float:
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise SettingValidationError(f"{spec.label}必须为数字") from exc
        if value < 0:
            raise SettingValidationError(f"{spec.label}不可为负数")
        return value
    if raw_value not in spec.enum_choices:
        choices = " / ".join(spec.enum_choices)
        raise SettingValidationError(f"{spec.label}只允许：{choices}")
    return raw_value


def update_values(db: Session, values: dict[str, str]) -> list[SystemSetting]:
    seed_defaults(db)
    for key, raw_value in values.items():
        _convert(key, raw_value)
    for key, raw_value in values.items():
        row = db.query(SystemSetting).filter(SystemSetting.key == key).one()
        row.value = raw_value
    db.commit()
    return list_settings(db)


def reset_defaults(db: Session) -> list[SystemSetting]:
    db.query(SystemSetting).delete()
    db.commit()
    seed_defaults(db)
    return list_settings(db)


def get_setting(db: Session, key: str) -> int | float | str:
    _ensure_defaults(db)
    row = db.query(SystemSetting).filter(SystemSetting.key == key).one()
    return _convert(key, row.value)
