import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from proxmoxer import ProxmoxAPI
from pydantic import BaseModel

from ..common import app_state
from ..db import get_logs_session_context
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


def _start_guest_exec(proxmox_api: ProxmoxAPI, node: str, vmid: int, cmd: str) -> int:
    exec_data = ExecData(command=[cmd], node=node, vmid=vmid)
    exec_response: dict = (
        proxmox_api.nodes(node).qemu(vmid).agent("exec").post(**exec_data.model_dump())
    )
    return exec_response.get("pid", -1)


def _get_guest_exec_status(
    proxmox_api: ProxmoxAPI, node: str, vmid: int, pid: int
) -> dict[str, Any]:
    return (
        proxmox_api.nodes(node)
        .qemu(vmid)
        .agent("exec-status")
        .get(node=node, vmid=vmid, pid=pid)
    )


async def run_invocation(invocation_id: int | None) -> None:
    if invocation_id is None:
        return
    with get_logs_session_context() as session:
        db_invocation = session.get(Invocation, invocation_id)
        if not db_invocation:
            return
        invocation_response = InvocationResponse.model_validate(
            db_invocation.model_dump()
        )
    # logger.info(invocation_response.model_dump_json(indent=2))

    def match_all_guests(proxmox_api: ProxmoxAPI):
        nodes_list = proxmox_api.nodes.get()
        matched_vms_by_node: dict[str, list[dict[str, Any]]] = {}
        for node_info in nodes_list:
            node = node_info["node"]
            matched_vms_by_node[node] = []
            if node_info["status"] != "online":
                continue
            node_vms = proxmox_api.nodes(node).qemu.get()
            # print(json.dumps(node_vms, indent=2))
            for vm in node_vms:
                if check_vm_match(
                    PveQemuVm.model_validate(vm), invocation_response.exec_config
                ):
                    matched_vms_by_node[node].append(vm)

        return matched_vms_by_node

    matched_vms_by_node = await run_in_pve_worker(app_state.queue, match_all_guests)
    # print(json.dumps(matched_vms_by_node, indent=2))

    async def execute_guest(invocation_guest: InvocationGuest) -> None:
        node = invocation_guest.node
        vmid = invocation_guest.vmid
        cmd = invocation_response.cmd_template.template

        try:
            pid = await run_in_pve_worker(
                app_state.queue, _start_guest_exec, [node, vmid, cmd]
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to start exec on {node}/{vmid}: {exc}")
            invocation_guest.exec_message = f"error starting: {exc}"
            return

        if pid <= 0:
            invocation_guest.exec_message = "error starting (invalid pid)"
            return

        invocation_guest.exec_pid = pid
        start_time = time.monotonic()
        process_exited = False
        exec_status_response: dict[str, Any] = {}

        while (
            not process_exited and (time.monotonic() - start_time) < EXEC_WAIT_TIMEOUT
        ):
            await asyncio.sleep(0.5)
            try:
                exec_status_response = await run_in_pve_worker(
                    app_state.queue, _get_guest_exec_status, [node, vmid, pid]
                )
                process_exited = bool(exec_status_response.get("exited", False))
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"Error checking exec-status on {node}/{vmid} pid={pid}: {exc}"
                )

        invocation_guest.exec_message = (
            f"done ({exec_status_response.get('exitcode', '-')})"
        )
        exec_status = dict(exec_status_response)
        if "out-data" in exec_status and isinstance(exec_status["out-data"], str):
            # write only the tail of stdout
            exec_status["out-data"] = exec_status["out-data"][-200:]
        if "err-data" in exec_status and isinstance(exec_status["err-data"], str):
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
                tasks.append(execute_guest(invocation_guest))

    with get_logs_session_context() as session:
        db_invocation = session.get(Invocation, invocation_id)
        if db_invocation:
            db_invocation.matched_guests_json = json.dumps(
                [invocation_guest.model_dump() for invocation_guest in matched_vms]
            )
            session.add(db_invocation)
            session.commit()

    _task_results = await asyncio.gather(*tasks)

    with get_logs_session_context() as session:
        db_invocation = session.get(Invocation, invocation_id)
        if db_invocation:
            db_invocation.matched_guests_json = json.dumps(
                [invocation_guest.model_dump() for invocation_guest in matched_vms]
            )
            db_invocation.finished_at = datetime.now(timezone.utc)
            session.add(db_invocation)
            session.commit()
