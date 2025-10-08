from fastapi import APIRouter, HTTPException
from sqlmodel import select

from ..db import SessionDep
from .models import CmdTemplate, CmdTemplateBase

router = APIRouter()


@router.get("/", response_model=list[CmdTemplate])
def get_cmd_templates(session: SessionDep):
    cmd_templates = session.exec(select(CmdTemplate)).all()
    return cmd_templates


@router.post("/", response_model=CmdTemplate)
def create_cmd_template(
    session: SessionDep, cmd_template: CmdTemplateBase
) -> CmdTemplate:
    """Create a new cmd template"""

    db_cmd_template = CmdTemplate.model_validate(cmd_template)
    session.add(db_cmd_template)
    session.commit()
    session.refresh(db_cmd_template)
    return db_cmd_template


@router.get("/{cmd_template_id}")
def read_cmd_template(session: SessionDep, cmd_template_id: int) -> CmdTemplate:
    """Read an cmd template by id"""

    db_cmd_template = session.get(CmdTemplate, cmd_template_id)
    if not db_cmd_template:
        raise HTTPException(status_code=404, detail="CmdTemplate not found")
    return db_cmd_template


@router.put("/{cmd_template_id}")
def update_cmd_template(
    session: SessionDep, cmd_template_id: int, cmd_template: CmdTemplateBase
) -> CmdTemplate:
    """Update an existing cmd template"""

    db_cmd_template = session.get(CmdTemplate, cmd_template_id)
    if not db_cmd_template:
        raise HTTPException(status_code=404, detail="CmdTemplate not found")

    cmd_template_data = cmd_template.model_dump()
    db_cmd_template.sqlmodel_update(cmd_template_data)
    session.commit()
    session.refresh(db_cmd_template)
    return db_cmd_template


@router.delete("/{cmd_template_id}")
def delete_cmd_template(session: SessionDep, cmd_template_id: int):
    """Delete an cmd template by id"""

    db_cmd_template = session.get(CmdTemplate, cmd_template_id)
    if not db_cmd_template:
        raise HTTPException(status_code=404, detail="CmdTemplate not found")

    session.delete(db_cmd_template)
    session.commit()

    return {"status": "deleted", "id": cmd_template_id}
