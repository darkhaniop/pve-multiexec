from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import pve_multiexec.pve.worker as worker_mod
from pve_multiexec.app import app
from pve_multiexec.db import _LocalState, get_logs_session, get_session


@pytest.fixture(name="engine")
def engine_fixture():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    _LocalState.engine = test_engine
    _LocalState.logs_engine = test_engine
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


@pytest.fixture(name="mock_proxmox_api")
def mock_proxmox_api_fixture(monkeypatch):
    mock_api = MagicMock()
    monkeypatch.setattr(worker_mod, "create_proxmox_api", lambda: mock_api)
    # Clear thread-local proxmox_api so mock is picked up
    if hasattr(worker_mod._thread_local, "proxmox_api"):
        delattr(worker_mod._thread_local, "proxmox_api")
    yield mock_api
    if hasattr(worker_mod._thread_local, "proxmox_api"):
        delattr(worker_mod._thread_local, "proxmox_api")


@pytest.fixture(name="client")
def client_fixture(
    session: Session, mock_proxmox_api
) -> Generator[TestClient, None, None]:
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_logs_session] = override_get_session

    test_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="test-pve")
    worker_mod.set_pve_executor(test_executor)
    app.state.executor = test_executor

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    test_executor.shutdown(wait=True)
    worker_mod.set_pve_executor(None)
