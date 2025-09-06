from fastapi import APIRouter

from .models import CmdTemplate, CmdTemplateBase

router = APIRouter()


@router.get("/")
async def get_cmd_templates():
    return []


@router.post("/")
async def create_cmd_template(cmd_template: CmdTemplateBase) -> CmdTemplate:
    """Create a new cmd template"""

    db_cmd_template = CmdTemplate.model_validate(cmd_template)
    return db_cmd_template


@router.get("/{cmd_template_id}")
async def read_cmd_template(cmd_template_id: int) -> CmdTemplate:
    """Read an cmd template by id"""

    db_cmd_template = CmdTemplate.model_validate({})
    return db_cmd_template


@router.put("/{cmd_template_id}")
async def update_cmd_template(
    cmd_template_id: int, cmd_template: CmdTemplateBase
) -> CmdTemplate:
    """Update an existing cmd template"""

    db_cmd_template = CmdTemplate.model_validate(cmd_template)
    return db_cmd_template


@router.delete("/{cmd_template_id}")
async def delete_cmd_template(cmd_template_id: int):
    """Delete an cmd template by id"""

    return
