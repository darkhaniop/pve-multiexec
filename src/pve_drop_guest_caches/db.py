from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from .api_cmd_templates.models import db_init as cmd_templates_db_init
from .common import app_state


class _LocalState:
    engine: Engine


def db_init():
    cmd_templates_db_init()

    sqlite_file_name = app_state.config["db_file"]
    sqlite_url = f"sqlite:///{sqlite_file_name}"

    connect_args = {"check_same_thread": False}
    _LocalState.engine = create_engine(sqlite_url, connect_args=connect_args)

    SQLModel.metadata.create_all(_LocalState.engine)


def get_session():
    with Session(_LocalState.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
