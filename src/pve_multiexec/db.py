from contextlib import contextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from .api_cmd_templates.models import db_init as cmd_templates_db_init
from .api_exec_configs.models import db_init as exec_configs_db_init
from .api_invocations.models import db_init as invocations_db_init
from .common import app_state


class _LocalState:
    engine: Engine
    logs_engine: Engine


def db_init():
    cmd_templates_db_init()
    exec_configs_db_init()
    invocations_db_init()

    sqlite_file_name = app_state.config["db_file"]
    sqlite_url = f"sqlite:///{sqlite_file_name}"

    connect_args = {"check_same_thread": False}
    _LocalState.engine = create_engine(sqlite_url, connect_args=connect_args)

    # If used heavily, it'd be better to use a separate db file (or an external tool) for logs
    # For now, logs will go into the the main db
    _LocalState.logs_engine = _LocalState.engine

    SQLModel.metadata.create_all(_LocalState.engine)


@contextmanager
def get_session_context():
    with Session(_LocalState.engine) as session:
        yield session


def get_session():
    with get_session_context() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@contextmanager
def get_logs_session_context():
    with Session(_LocalState.logs_engine) as session:
        yield session


def get_logs_session():
    with get_logs_session_context() as session:
        yield session


LogsSessionDep = Annotated[Session, Depends(get_logs_session)]
