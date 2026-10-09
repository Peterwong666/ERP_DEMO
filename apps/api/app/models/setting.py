from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import SettingCategory, SettingValueType


class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"

    setting_id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    value: Mapped[str] = mapped_column(String(255))
    value_type: Mapped[SettingValueType] = mapped_column(
        Enum(SettingValueType, native_enum=False, length=16)
    )
    category: Mapped[SettingCategory] = mapped_column(
        Enum(SettingCategory, native_enum=False, length=32), index=True
    )
    label: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(255))
