import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from proxmoxer import ProxmoxAPI
from pydantic import BaseModel
from sqlmodel import Session

from ..common import app_state
from ..pve.schemas import PveQemuVm
from ..pve.worker import run_in_pve_worker
from .models import Invocation
from .utils import InvocationGuest, InvocationResponse, check_vm_match

EXEC_WAIT_TIMEOUT = 3600


logger = logging.getLogger(__name__)


class ExecData(BaseModel):
    command: list[str]
    node: str
    vmid: int


async def run_invocation(invocation_id: int | None, logs_session: Session) -> None:
    if invocation_id is None:
        return
    db_invocation = logs_session.get(Invocation, invocation_id)
    if not db_invocation:
        return
    invocation_response = InvocationResponse.model_validate(db_invocation.model_dump())
    # logger.info(invocation_response.model_dump_json(indent=2))

    return_value = {"nodes": None, "vms_by_node": {}}

    def match_all_guests(proxmox_api: ProxmoxAPI):
        return_value["nodes"] = proxmox_api.nodes.get()

        vms_by_node: dict[str, list[dict[str, Any]]] = {}
        matched_vms_by_node = {}
        for node_info in return_value["nodes"]:
            node = node_info["node"]
            matched_vms_by_node[node] = []
            if node_info["status"] != "online":
                continue
            vms_by_node[node] = proxmox_api.nodes(node).qemu.get()
            # print(json.dumps(vms_by_node[node], indent=2))
            for vm in vms_by_node[node]:
                if check_vm_match(
                    PveQemuVm.model_validate(vm), invocation_response.exec_config
                ):
                    matched_vms_by_node[node].append(vm)

        return_value["vms_by_node"] = vms_by_node
        return_value["matched_vms_by_node"] = matched_vms_by_node
        return matched_vms_by_node

    # def get_matches():
    #     worker_job = WorkerJob(match_all_guests, threading.Event())
    #     app_state.queue.put(worker_job)
    #     worker_job.done_event.wait()
    #     return return_value["matched_vms_by_node"]

    # matched_vms_by_node = await asyncio.to_thread(get_matches)

    matched_vms_by_node = await run_in_pve_worker(app_state.queue, match_all_guests)
    # print(json.dumps(matched_vms_by_node, indent=2))

    def exec_starter(proxmox_api: ProxmoxAPI, invocation_guest: InvocationGuest):
        node = invocation_guest.node
        vmid = invocation_guest.vmid

        exec_data = ExecData(
            command=[invocation_response.cmd_template.template], node=node, vmid=vmid
        )
        exec_response: dict = (
            proxmox_api.nodes(node)
            .qemu(vmid)
            .agent("exec")
            .post(**exec_data.model_dump())
        )
        pid: int = exec_response.get("pid", -1)
        if pid <= 0:
            # error
            return
        invocation_guest.exec_pid = pid

        start_time = time.monotonic()
        duration = 0
        exec_status_params = {"node": node, "vmid": vmid, "pid": pid}
        process_exited = False
        while not process_exited and duration < EXEC_WAIT_TIMEOUT:
            time.sleep(0.4)
            exec_status_response: dict[str, Any] = (
                proxmox_api.nodes(node)
                .qemu(vmid)
                .agent("exec-status")
                .get(**exec_status_params)
            )
            process_exited: bool = exec_status_response.get("exited", False)
            duration = time.monotonic() - start_time

        invocation_guest.exec_message = (
            f"done ({exec_status_response.get('exitcode', '-')})"
        )
        exec_status = json.loads(json.dumps(exec_status_response))
        if "out-data" in exec_status:
            # write only the tail of stdout
            exec_status["out-data"] = exec_status["out-data"][-200:]
        if "err-data" in exec_status:
            # write only the tail of stderr
            exec_status["err-data"] = exec_status["err-data"][-200:]
        invocation_guest.exec_status = exec_status

    matched_vms = []
    tasks = []
    for node, vms in matched_vms_by_node.items():
        for vm in vms:
            vmid = vm["vmid"]
            exec_flag = vm["status"] == "running"
            exec_message = "done (vm not running)" if not exec_flag else "scheduled"

            invocation_guest = InvocationGuest(
                node=node,
                vmid=vmid,
                exec_flag=exec_flag,
                exec_message=exec_message,
                vm_info=vm,
            )
            matched_vms.append(invocation_guest)

            if exec_flag:
                tasks.append(
                    run_in_pve_worker(app_state.queue, exec_starter, [invocation_guest])
                )

    db_invocation.matched_guests_json = json.dumps(
        [invocation_guest.model_dump() for invocation_guest in matched_vms]
    )
    logs_session.add(db_invocation)
    logs_session.commit()

    _task_results = await asyncio.gather(*tasks)

    db_invocation.matched_guests_json = json.dumps(
        [invocation_guest.model_dump() for invocation_guest in matched_vms]
    )
    db_invocation.finished_at = datetime.now(timezone.utc)
    logs_session.add(db_invocation)
    logs_session.commit()
