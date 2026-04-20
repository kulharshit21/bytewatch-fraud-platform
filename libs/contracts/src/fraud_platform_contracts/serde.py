from __future__ import annotations

from typing import Any, TypeVar

import orjson
from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def dump_json(model: BaseModel) -> bytes:
    return orjson.dumps(model.model_dump(mode="json"))


def dump_json_str(model: BaseModel) -> str:
    return dump_json(model).decode("utf-8")


def load_json(model_cls: type[ModelT], payload: bytes | str | dict[str, Any]) -> ModelT:
    if isinstance(payload, dict):
        return model_cls.model_validate(payload)
    if isinstance(payload, bytes):
        return model_cls.model_validate(orjson.loads(payload))
    return model_cls.model_validate(orjson.loads(payload.encode("utf-8")))
