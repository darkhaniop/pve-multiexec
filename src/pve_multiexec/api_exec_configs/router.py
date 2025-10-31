import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, BeforeValidator, Field
from sqlmodel import Session, select

from ..api_cmd_templates.models import CmdTemplate
from ..common.utils import to_list_validator
from ..db import SessionDep
from .models import ExecConfig, ExecConfigBase

router = APIRouter()


class ExecConfigUpdate(BaseModel):
    name: str = Field(min_length=1)
    include_tags: list[str]
    exclude_tags: list[str]
    include_vmids: list[int]
    cmd_template_id: int | None


class ExecConfigResult(ExecConfigUpdate):
    id: int
    name: str
    include_tags: Annotated[list[str], BeforeValidator(to_list_validator)]
    exclude_tags: Annotated[list[str], BeforeValidator(to_list_validator)]
    include_vmids: Annotated[list[int], BeforeValidator(to_list_validator)]
    cmd_template_id: int | None


def get_exec_config_by_id(session: SessionDep, exec_config_id: int) -> ExecConfig:
    db_exec_config = session.get(ExecConfig, exec_config_id)
    if not db_exec_config:
        raise HTTPException(status_code=404, detail="ExecConfig not found")
    return db_exec_config


DbExecConfigDep = Annotated[ExecConfig, Depends(get_exec_config_by_id)]


def serialize_exec_config_fields(exec_config: ExecConfigUpdate) -> ExecConfigBase:
    STR_FIELDS = ["include_tags", "exclude_tags", "include_vmids"]

    exec_config_obj = exec_config.model_dump()
    return ExecConfigBase.model_validate(
        {
            **exec_config_obj,
            **{field: json.dumps(exec_config_obj[field]) for field in STR_FIELDS},
        }
    )


def validate_and_prepare_exec_config(
    session: Session, exec_config: ExecConfigUpdate
) -> ExecConfigBase:
    cmd_template_id = exec_config.cmd_template_id
    if cmd_template_id is not None:
        db_cmd_template = session.get(CmdTemplate, cmd_template_id)
        if not db_cmd_template:
            raise HTTPException(
                status_code=404,
                detail=f"CmdTemplate with id={cmd_template_id} not found",
            )

    return serialize_exec_config_fields(exec_config)


@router.get("/", response_model=list[ExecConfigResult])
def get_exec_configs(
    session: SessionDep,
    offset: int = Query(default=0, ge=0, description="Offset for pagination."),
    limit: int = Query(default=50, ge=1, le=100, description="Limit for pagination."),
):
    """Read a subset of ExecConfigs"""

    exec_configs = session.exec(select(ExecConfig).offset(offset).limit(limit)).all()
    return exec_configs


@router.post("/", response_model=ExecConfigResult, status_code=status.HTTP_201_CREATED)
def create_exec_config(
    session: SessionDep, exec_config_in: ExecConfigUpdate
) -> ExecConfig:
    """Create a new ExecConfig"""

    valid_exec_config = validate_and_prepare_exec_config(session, exec_config_in)
    db_exec_config = ExecConfig.model_validate(valid_exec_config)
    session.add(db_exec_config)
    session.commit()
    session.refresh(db_exec_config)
    return db_exec_config


@router.get("/{exec_config_id}", response_model=ExecConfigResult)
def read_exec_config(db_exec_config: DbExecConfigDep) -> ExecConfig:
    """Read an ExecConfig by id"""

    return db_exec_config


@router.put("/{exec_config_id}", response_model=ExecConfigResult)
def update_exec_config(
    session: SessionDep,
    db_exec_config: DbExecConfigDep,
    exec_config_in: ExecConfigUpdate,
) -> ExecConfig:
    """Update an existing ExecConfig"""

    valid_exec_config = validate_and_prepare_exec_config(session, exec_config_in)
    exec_config_data = valid_exec_config.model_dump()
    db_exec_config.sqlmodel_update(exec_config_data)
    session.commit()
    session.refresh(db_exec_config)
    return db_exec_config


@router.delete("/{exec_config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exec_config(session: SessionDep, db_exec_config: DbExecConfigDep) -> None:
    """Delete an ExecConfig by id"""

    session.delete(db_exec_config)
    session.commit()
