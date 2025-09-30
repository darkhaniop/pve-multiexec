import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    Field,
    SerializerFunctionWrapHandler,
    computed_field,
    model_serializer,
)

from ..api_cmd_templates.models import CmdTemplateBase
from ..api_exec_configs.router import ExecConfigResult


class InvocationGuest(BaseModel):
    node: str
    vmid: int
    vm_info: Mapping[str, Any]
    exec_flag: bool
    exec_message: str = ""
    exec_status: Mapping[str, Any] | None = None


class InvocationResult(BaseModel):
    id: int
    exec_config_id: int
    cmd_template_id: int
    exec_config_raw: str
    cmd_template_raw: str
    matched_guests_json: str = Field(exclude=True)
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

    @computed_field
    @property
    def matched_guests(self) -> list[InvocationGuest]:
        return json.loads(self.matched_guests_json)


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
