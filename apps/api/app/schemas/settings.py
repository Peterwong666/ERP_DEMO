from pydantic import BaseModel


class SettingOut(BaseModel):
    key: str
    value: str
    value_type: str
    category: str
    label: str
    description: str


class SettingsUpdate(BaseModel):
    values: dict[str, str]
