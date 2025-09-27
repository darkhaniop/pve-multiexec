import json
from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    SerializerFunctionWrapHandler,
    computed_field,
    model_serializer,
)


def to_list_validator(value: str):
    if value is None:
        return []
    return json.loads(value)


class InvocationResult(BaseModel):
    id: int
    exec_config_id: int
    cmd_template_id: int
    exec_config_raw: str
    cmd_template_raw: str
    matched_guests: Annotated[
        list[Mapping[str, Any]], BeforeValidator(to_list_validator)
    ]
    created_at: datetime
    finished_dt: datetime | None

    @computed_field
    @property
    def duration_s(self) -> int | None:
        if self.finished_dt is None:
            return None
        return (self.finished_dt - self.created_at).seconds

    @computed_field
    @property
    def exec_config(self) -> Mapping[str, Any]:
        return json.loads(self.exec_config_raw)

    @computed_field
    @property
    def cmd_template(self) -> Mapping[str, Any]:
        return json.loads(self.cmd_template_raw)


class NewInvocation(BaseModel):
    exec_config_id: int
    use_custom_comment: bool = False
    comment: str | None = None

    @model_serializer(mode="wrap")
    def serialize_model(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, object]:
        serialized = handler(self)
        serialized["fields"] = list(serialized)
        return serialized
