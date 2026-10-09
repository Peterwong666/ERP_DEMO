"""API 枚举统一走 name 的可复用标注。

StrEnum 的 value 是中文展示标签，Pydantic 默认按 value 校验、
SQLAlchemy 按 name 持久化，两层标识不一致。wire_enum 把 HTTP
契约固定为 name（与 DB 一致），value 仅用于页面展示映射。
"""

from enum import Enum
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer


def _resolve_by_name(enum_cls: type[Enum]):
    def resolve(value: object) -> object:
        if isinstance(value, enum_cls):
            return value
        if isinstance(value, str):
            try:
                return enum_cls[value]
            except KeyError:
                return value
        return value

    return resolve


def wire_enum(enum_cls: type[Enum]):
    return Annotated[
        enum_cls,
        BeforeValidator(_resolve_by_name(enum_cls)),
        PlainSerializer(lambda member: member.name, return_type=str),
    ]
