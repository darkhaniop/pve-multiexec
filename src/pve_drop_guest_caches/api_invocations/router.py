import json
from collections.abc import Mapping
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter
from pydantic import BaseModel, BeforeValidator, computed_field
from sqlmodel import select

from pve_drop_guest_caches.api_invocations.models import Invocation

from ..db import LogsSessionDep

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
    vms_matched: Annotated[list[Mapping[str, Any]], BeforeValidator(to_list_validator)]
    vms_executed: Annotated[list[Mapping[str, Any]], BeforeValidator(to_list_validator)]
    created_at: datetime
    finished_dt: datetime | None

    @computed_field
    @property
    def duration_s(self) -> int | None:
        if self.finished_dt is None:
            return None
        return (self.finished_dt - self.created_at).seconds


@router.get("/", response_model=list[InvocationResult])
async def get_invocations(session: LogsSessionDep):
    """Read a subset of Invocations"""

    db_invocations = session.exec(select(Invocation)).all()
    return db_invocations
