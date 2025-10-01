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
from ..pve.schemas import PveQemuVm


class InvocationGuest(BaseModel):
    node: str
    vmid: int
    vm_info: Mapping[str, Any]
    exec_flag: bool
    exec_message: str = ""
    exec_pid: int = 0
    exec_status: Mapping[str, Any] | None = None


class InvocationResponse(BaseModel):
    id: int
    exec_config_id: int
    cmd_template_id: int
    exec_config_json: str = Field(exclude=True)
    cmd_template_json: str = Field(exclude=True)
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
        return ExecConfigResult.model_validate_json(self.exec_config_json)

    @computed_field
    @property
    def cmd_template(self) -> CmdTemplateBase:
        return CmdTemplateBase.model_validate_json(self.cmd_template_json)

    @computed_field
    @property
    def matched_guests(self) -> list[InvocationGuest]:
        return [
            InvocationGuest.model_validate(obj)
            for obj in json.loads(self.matched_guests_json)
        ]


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


def check_vm_match(vm: PveQemuVm, exec_config: ExecConfigResult) -> bool:
    # print(json.dumps(vm, indent=2))
    tags: list[str] = vm.tags.split(";") if vm.tags is not None else []

    found_in_includes = False
    for tag in tags:
        if tag in exec_config.include_tags:
            found_in_includes = True
            break
    found_in_excludes = False
    for tag in tags:
        if tag in exec_config.exclude_tags:
            found_in_excludes = True
            break
    if found_in_includes and not found_in_excludes:
        return True

    if vm.vmid in exec_config.include_vmids:
        return True

    return False
