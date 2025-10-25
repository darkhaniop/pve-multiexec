from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlmodel import select

from ..api_cmd_templates.models import CmdTemplate
from ..api_exec_configs.router import ExecConfigResult, get_exec_config_by_id
from ..db import LogsSessionDep, SessionDep
from .background import run_invocation
from .models import Invocation
from .utils import InvocationResponse, NewInvocation

router = APIRouter()


@router.get("/", response_model=list[InvocationResponse])
def get_invocations(session: LogsSessionDep):
    """Read a subset of Invocations"""

    db_invocations = session.exec(select(Invocation)).all()
    return db_invocations


@router.post(
    "/", response_model=InvocationResponse, status_code=status.HTTP_201_CREATED
)
def create_invocation(
    background_tasks: BackgroundTasks,
    session: SessionDep,
    logs_session: LogsSessionDep,
    new_invocation: NewInvocation,
) -> Invocation:
    """Create a new batch command invocation and trigger background execution."""
    exec_config_id = new_invocation.exec_config_id
    db_exec_config = get_exec_config_by_id(session, exec_config_id)
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

    db_invocation = Invocation(
        comment=comment,
        exec_config_id=exec_config_id,
        cmd_template_id=cmd_template_id,
        exec_config_json=exec_config.model_dump_json(indent=2),
        cmd_template_json=db_cmd_template.model_dump_json(indent=2),
        matched_guests_json="[]",
        finished_at=None,
    )
    logs_session.add(db_invocation)
    logs_session.commit()
    logs_session.refresh(db_invocation)

    background_tasks.add_task(run_invocation, db_invocation.id)

    return db_invocation
