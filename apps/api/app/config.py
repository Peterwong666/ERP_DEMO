from datetime import date

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ERP_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = "sqlite:///./erp_demo.db"

    # 种子数据锚点日期：无参调用 /api/dashboard 时默认按该日期计算，
    # 避免换日期演示时指标静默失真（可用 ERP_DATA_ANCHOR_DATE 覆盖）
    data_anchor_date: date = date(2026, 10, 9)
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
