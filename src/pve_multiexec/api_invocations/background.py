import asyncio
import json
import logging
import threading
from collections.abc import Mapping

from proxmoxer import ProxmoxAPI
from sqlmodel import Session

from pve_multiexec.common import app_state
from pve_multiexec.pve.worker import WorkerJob

from .models import Invocation
from .utils import InvocationResult

logger = logging.getLogger(__name__)


async def run_invocation(invocation_id: int | None, logs_session: Session) -> None:
    if invocation_id is None:
        return
    db_invocation = logs_session.get(Invocation, invocation_id)
    if not db_invocation:
        return
    invocation_result = InvocationResult.model_validate(db_invocation.model_dump())
    logger.info(invocation_result.model_dump_json(indent=2))

    return_value = {"nodes": None, "vms_by_node": {}}

    def check_vm_match(vm: dict, exec_config: Mapping) -> bool:
        # print(json.dumps(vm, indent=2))
        if "tags" not in vm or vm["tags"] is None:
            tags = []
        else:
            tags = vm["tags"].split(";")

        found_in_includes = False
        for tag in tags:
            if tag in exec_config["include_tags"]:
                found_in_includes = True
                break
        found_in_excludes = False
        for tag in tags:
            if tag in exec_config["exclude_tags"]:
                found_in_excludes = True
                break
        if found_in_includes and not found_in_excludes:
            return True

        if vm["vmid"] in exec_config["include_vmids"]:
            return True

        return False

    def fetch_all_guests(proxmox_api: ProxmoxAPI):
        return_value["nodes"] = proxmox_api.nodes.get()

        vms_by_node = {}
        matched_vms_by_node = {}
        for node_info in return_value["nodes"]:
            node = node_info["node"]
            matched_vms_by_node[node] = []
            if node_info["status"] != "online":
                continue
            vms_by_node[node] = proxmox_api.nodes(node).qemu.get()
            # print(json.dumps(vms_by_node[node], indent=2))
            for vm in vms_by_node[node]:
                if check_vm_match(vm, invocation_result.exec_config):
                    matched_vms_by_node[node].append(vm)

        return_value["vms_by_node"] = vms_by_node
        return_value["matched_vms_by_node"] = matched_vms_by_node

    def get_matches():
        worker_job = WorkerJob(fetch_all_guests, threading.Event())
        app_state.queue.put(worker_job)
        worker_job.done_event.wait()
        return return_value["matched_vms_by_node"]

    matched_vms_by_node = await asyncio.to_thread(get_matches)
    print(json.dumps(matched_vms_by_node, indent=2))
