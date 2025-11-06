from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def test_get_nodes_success(client: TestClient, mock_proxmox_api: MagicMock):
    mock_proxmox_api.nodes.get.return_value = [
        {"node": "node1", "status": "online", "cpu": 0.1, "mem": 1024, "maxmem": 4096},
        {"node": "node2", "status": "offline"},
    ]

    response = client.get("/nodes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["node"] == "node1"
    assert data[0]["status"] == "online"
    assert data[1]["node"] == "node2"


def test_get_node_vms_success(client: TestClient, mock_proxmox_api: MagicMock):
    mock_node = MagicMock()
    mock_proxmox_api.nodes.return_value = mock_node
    mock_node.qemu.get.return_value = [
        {"vmid": 100, "name": "vm1", "status": "running", "qmpstatus": "running"},
        {"vmid": 101, "name": "vm2", "status": "stopped", "qmpstatus": "stopped"},
    ]

    response = client.get("/nodes/node1/vms")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["vmid"] == 100
    assert data[0]["status"] == "running"


def test_get_node_vms_unavailable(client: TestClient, mock_proxmox_api: MagicMock):
    mock_node = MagicMock()
    mock_proxmox_api.nodes.return_value = mock_node
    mock_node.qemu.get.side_effect = Exception("Node offline")

    response = client.get("/nodes/invalid-node/vms")
    assert response.status_code == 404
