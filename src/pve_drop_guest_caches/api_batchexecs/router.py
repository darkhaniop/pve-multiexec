from fastapi import APIRouter
from sqlmodel import select

from ..db import SessionDep
from .models import BatchExec

router = APIRouter()


@router.get("/", response_model=list[BatchExec])
async def get_cmd_templates(session: SessionDep):
    cmd_templates = session.exec(select(BatchExec)).all()
    return cmd_templates
