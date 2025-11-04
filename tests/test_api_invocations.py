import pytest
from fastapi.testclient import TestClient


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
