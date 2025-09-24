import json
from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import (
    BaseModel,
    BeforeValidator,
    SerializerFunctionWrapHandler,
    computed_field,
    model_serializer,
)
from sqlmodel import select

from ..api_cmd_templates.models import CmdTemplate
from ..api_exec_configs.router import ExecConfigResult, get_exec_config_by_id
from ..db import LogsSessionDep, SessionDep
from .background import run_invocation
from .models import Invocation, InvocationBase

router = APIRouter()


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


async def get_db_invocation_from_new(
    background_tasks: BackgroundTasks,
    session: SessionDep,
    new_invocation: NewInvocation,
) -> Invocation:
    exec_config_id = new_invocation.exec_config_id
    db_exec_config = await get_exec_config_by_id(session, exec_config_id)
    exec_config = ExecConfigResult.model_validate(db_exec_config.model_dump())
    cmd_template_id = db_exec_config.cmd_template_id
    if cmd_template_id is None:
        raise HTTPException(
            status_code=422,
            detail="CmdTemplate id is not specified in the selected ExecConfig",
        )
    db_cmd_template = session.get(CmdTemplate, cmd_template_id)
    if not db_cmd_template:
        raise HTTPException(status_code=404, detail="CmdTemplate not found")

    comment = "no-custom-comment"
    if new_invocation.use_custom_comment:
        comment = new_invocation.comment if new_invocation.comment is not None else ""

    new_invocation_base = InvocationBase.model_validate(
        {
            "comment": comment,
            "exec_config_id": exec_config_id,
            "cmd_template_id": cmd_template_id,
            "exec_config_raw": exec_config.model_dump_json(indent=2),
            "cmd_template_raw": db_cmd_template.model_dump_json(indent=2),
            "matched_guests": "[]",
            "finished_dt": None,
        }
    )

    db_invocation = Invocation.model_validate(new_invocation_base)
    session.add(db_invocation)
    session.commit()
    session.refresh(db_invocation)

    background_tasks.add_task(run_invocation, db_invocation)

    return db_invocation


DbInvocationFromNewDep = Annotated[InvocationBase, Depends(get_db_invocation_from_new)]


@router.get("/", response_model=list[InvocationResult])
async def get_invocations(session: LogsSessionDep):
    """Read a subset of Invocations"""

    db_invocations = session.exec(select(Invocation)).all()
    return db_invocations


@router.post("/", response_model=InvocationResult)
async def create_invocation(
    session: LogsSessionDep, db_invocation: DbInvocationFromNewDep
):
    return db_invocation
