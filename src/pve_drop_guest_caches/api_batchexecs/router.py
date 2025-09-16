import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, BeforeValidator, Field
from sqlmodel import select

from ..api_cmd_templates.models import CmdTemplate
from ..db import SessionDep
from .models import BatchExec, BatchExecBase

router = APIRouter()


class BatchExecUpdate(BaseModel):
    name: str = Field(min_length=1)
    include_tags: list[str]
    exclude_tags: list[str]
    include_vmids: list[int]
    cmd_template_id: int | None


def to_list_validator(value: str):
    if value is None:
        return []
    else:
        return json.loads(value)


class BatchExecResult(BatchExecUpdate):
    id: int
    name: str
    include_tags: Annotated[list[str], BeforeValidator(to_list_validator)]
    exclude_tags: Annotated[list[str], BeforeValidator(to_list_validator)]
    include_vmids: Annotated[list[int], BeforeValidator(to_list_validator)]
    cmd_template_id: int | None


async def get_exec_config_by_id(session: SessionDep, exec_config_id: int) -> BatchExec:
    db_exec_config = session.get(BatchExec, exec_config_id)
    if not db_exec_config:
        raise HTTPException(status_code=404, detail="ExecConfig not found")
    return db_exec_config


DbExecConfigDep = Annotated[BatchExec, Depends(get_exec_config_by_id)]


# include_tags: str
# exclude_tags: str
# include_vmids: str
def beu2beb(exec_config: BatchExecUpdate) -> BatchExecBase:
    STR_FIELDS = ["include_tags", "exclude_tags", "include_vmids"]

    exec_config_obj = exec_config.model_dump()
    print(exec_config_obj)
    return BatchExecBase.model_validate(
        {
            **exec_config_obj,
            **{field: json.dumps(exec_config_obj[field]) for field in STR_FIELDS},
        }
    )


async def get_valid_exec_config(
    session: SessionDep, exec_config: BatchExecUpdate
) -> BatchExecBase:
    cmd_template_id = exec_config.cmd_template_id
    if cmd_template_id is None:
        return beu2beb(exec_config)
    db_cmd_template = session.get(CmdTemplate, cmd_template_id)
    if not db_cmd_template:
        raise HTTPException(
            status_code=404, detail=f"CmdTemplate with id={cmd_template_id} not found"
        )

    return beu2beb(exec_config)


ValidExecConfigDep = Annotated[BatchExecBase, Depends(get_valid_exec_config)]


@router.get("/", response_model=list[BatchExecResult])
async def get_exec_config(session: SessionDep):
    """Read a subset of ExecConfigs"""

    exec_config = session.exec(select(BatchExec)).all()
    return exec_config


@router.post("/", response_model=BatchExecResult)
async def create_exec_config(session: SessionDep, new_exec_config: ValidExecConfigDep):
    """Create a new ExecConfig"""

    db_exec_config = BatchExec.model_validate(new_exec_config)
    session.add(db_exec_config)
    session.commit()
    session.refresh(db_exec_config)
    return db_exec_config


@router.get("/{exec_config_id}", response_model=BatchExecResult)
async def read_exec_config(db_exec_config: DbExecConfigDep):
    """Read an ExecConfig by id"""

    return db_exec_config


@router.put("/{exec_config_id}", response_model=BatchExecResult)
async def update_exec_config(
    session: SessionDep,
    db_exec_config: DbExecConfigDep,
    updated_exec_config: ValidExecConfigDep,
):
    """Update an existing ExecConfig"""

    exec_config_data = updated_exec_config.model_dump()
    db_exec_config.sqlmodel_update(exec_config_data)
    session.commit()
    session.refresh(db_exec_config)
    return db_exec_config


@router.delete("/{exec_config_id}")
async def delete_exec_config(session: SessionDep, db_exec_config: DbExecConfigDep):
    """Delete an ExecConfig by id"""

    exec_config_id = db_exec_config.id

    session.delete(db_exec_config)
    session.commit()

    return {"status": "deleted", "id": exec_config_id}
