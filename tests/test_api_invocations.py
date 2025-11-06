from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from pve_multiexec.api_invocations.background import run_invocation
from pve_multiexec.api_invocations.models import Invocation
from pve_multiexec.api_invocations.utils import InvocationResponse


def test_create_and_list_invocations(client: TestClient):
    # Setup: template & exec_config
    tpl_res = client.post(
        "/cmd_templates/",
        json={"name": "Check Uptime", "template": "uptime"},
    )
    tpl_id = tpl_res.json()["id"]

    cfg_res = client.post(
        "/exec_configs/",
        json={
            "name": "Dev Group",
            "include_tags": ["dev"],
            "exclude_tags": [],
            "include_vmids": [101],
            "cmd_template_id": tpl_id,
        },
    )
    cfg_id = cfg_res.json()["id"]

    # 1. Trigger invocation
    inv_res = client.post(
        "/invocations/",
        json={
            "exec_config_id": cfg_id,
            "use_custom_comment": True,
            "comment": "Scheduled run #1",
        },
    )
    assert inv_res.status_code == 201
    data = inv_res.json()
    assert data["exec_config_id"] == cfg_id
    assert data["cmd_template_id"] == tpl_id
    assert data["exec_config"]["name"] == "Dev Group"
    assert data["cmd_template"]["name"] == "Check Uptime"

    # 2. List invocations
    list_res = client.get("/invocations/?offset=0&limit=10")
    assert list_res.status_code == 200
    invocations = list_res.json()
    assert len(invocations) >= 1
    assert invocations[0]["id"] == data["id"]


def test_create_invocation_validation_errors(client: TestClient):
    # Non-existent exec config
    res = client.post(
        "/invocations/",
        json={"exec_config_id": 99999, "use_custom_comment": False},
    )
    assert res.status_code == 404

    # Exec config with no template
    cfg_no_tpl = client.post(
        "/exec_configs/",
        json={
            "name": "No Template Config",
            "include_tags": [],
            "exclude_tags": [],
            "include_vmids": [102],
            "cmd_template_id": None,
        },
    )
    no_tpl_id = cfg_no_tpl.json()["id"]

    res_no_tpl = client.post(
        "/invocations/",
        json={"exec_config_id": no_tpl_id, "use_custom_comment": False},
    )
    assert res_no_tpl.status_code == 422


@pytest.mark.asyncio
async def test_run_invocation_background_execution(
    session: Session, mock_proxmox_api: MagicMock
):
    # Setup mock PVE cluster
    mock_proxmox_api.nodes.get.return_value = [
        {"node": "pve1", "status": "online"},
        {"node": "pve2", "status": "offline"},
    ]

    # VMs on node pve1
    mock_pve1 = MagicMock()
    mock_proxmox_api.nodes.return_value = mock_pve1
    mock_pve1.qemu.get.return_value = [
        {"vmid": 101, "name": "web-01", "status": "running", "tags": "web;dev"},
        {"vmid": 102, "name": "db-01", "status": "stopped", "tags": "db;dev"},
    ]

    # Agent exec mock
    mock_qemu_101 = MagicMock()
    mock_pve1.qemu.return_value = mock_qemu_101
    mock_agent = MagicMock()
    mock_qemu_101.agent.return_value = mock_agent
    mock_agent.post.return_value = {"pid": 1234}
    mock_agent.get.return_value = {
        "exited": 1,
        "exitcode": 0,
        "out-data": "load average: 0.05",
    }

    # Create Invocation record in DB
    invocation = Invocation(
        comment="Test Background Run",
        exec_config_id=1,
        cmd_template_id=1,
        exec_config_json='{"id": 1, "name": "Dev", "include_tags": ["dev"], "exclude_tags": [], "include_vmids": [], "cmd_template_id": 1}',
        cmd_template_json='{"name": "Uptime", "template": "uptime"}',
        matched_guests_json="[]",
        finished_at=None,
    )
    session.add(invocation)
    session.commit()
    session.refresh(invocation)

    # Run background invocation orchestrator
    await run_invocation(invocation.id)

    # Re-fetch from DB and verify updates
    session.refresh(invocation)
    assert invocation.finished_at is not None

    inv_resp = InvocationResponse.model_validate(invocation.model_dump())
    assert len(inv_resp.matched_guests) == 2

    # Check running VM result
    running_guest = next(g for g in inv_resp.matched_guests if g.vmid == 101)
    assert running_guest.exec_flag is True
    assert running_guest.exec_pid == 1234
    assert "done (0)" in running_guest.exec_message
    assert running_guest.exec_status is not None

    # Check stopped VM result
    stopped_guest = next(g for g in inv_resp.matched_guests if g.vmid == 102)
    assert stopped_guest.exec_flag is False
    assert stopped_guest.exec_message == "done (vm not running)"
