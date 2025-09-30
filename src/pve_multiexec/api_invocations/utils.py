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

from ..api_cmd_templates.models import CmdTemplateBase
from ..api_exec_configs.router import ExecConfigResult
from ..common.utils import to_list_validator


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
    finished_at: datetime | None

    @computed_field
    @property
    def duration_s(self) -> int | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.created_at).seconds

    @computed_field
    @property
    def exec_config(self) -> ExecConfigResult:
        # return json.loads(self.exec_config_raw)
        return ExecConfigResult.model_validate_json(self.exec_config_raw)

    @computed_field
    @property
    def cmd_template(self) -> CmdTemplateBase:
        # return json.loads(self.cmd_template_raw)
        return CmdTemplateBase.model_validate_json(self.cmd_template_raw)


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
