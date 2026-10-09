from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.settings import SettingOut, SettingsUpdate
from app.services.settings_service import (
    SettingValidationError,
    list_settings,
    reset_defaults,
    update_values,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


def to_out(row: object) -> SettingOut:
    return SettingOut.model_validate(row, from_attributes=True)


@router.get("", response_model=list[SettingOut])
def get_settings(db: Session = Depends(get_db)) -> list[SettingOut]:
    return [to_out(row) for row in list_settings(db)]


@router.put("", response_model=list[SettingOut])
def put_settings(
    payload: SettingsUpdate, db: Session = Depends(get_db)
) -> list[SettingOut]:
    try:
        rows = update_values(db, payload.values)
    except SettingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [to_out(row) for row in rows]


@router.post("/reset", response_model=list[SettingOut])
def post_reset(db: Session = Depends(get_db)) -> list[SettingOut]:
    return [to_out(row) for row in reset_defaults(db)]
