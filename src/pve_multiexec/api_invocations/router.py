from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import select

from ..api_cmd_templates.models import CmdTemplate
from ..api_exec_configs.router import ExecConfigResult, get_exec_config_by_id
from ..db import LogsSessionDep, SessionDep
from .background import run_invocation
from .models import Invocation, InvocationBase
from .utils import InvocationResult, NewInvocation

router = APIRouter()


async def get_db_invocation_from_new(
    background_tasks: BackgroundTasks,
    session: SessionDep,
    logs_session: LogsSessionDep,
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

    # new_invocation_base = InvocationBase.model_validate(
    #     {
    #         "comment": comment,
    #         "exec_config_id": exec_config_id,
    #         "cmd_template_id": cmd_template_id,
    #         "exec_config_raw": exec_config.model_dump_json(indent=2),
    #         "cmd_template_raw": db_cmd_template.model_dump_json(indent=2),
    #         "matched_guests_json": "[]",
    #         "finished_at": None,
    #     }
    # )
    # db_invocation = Invocation.model_validate(new_invocation_base)
    db_invocation = Invocation(
        **{
            "comment": comment,
            "exec_config_id": exec_config_id,
            "cmd_template_id": cmd_template_id,
            "exec_config_raw": exec_config.model_dump_json(indent=2),
            "cmd_template_raw": db_cmd_template.model_dump_json(indent=2),
            "matched_guests_json": "[]",
            "finished_at": None,
        }
    )
    logs_session.add(db_invocation)
    logs_session.commit()
    logs_session.refresh(db_invocation)

    background_tasks.add_task(run_invocation, db_invocation.id, logs_session)

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
