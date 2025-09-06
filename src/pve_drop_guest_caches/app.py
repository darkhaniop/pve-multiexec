import asyncio
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI
from proxmoxer import ProxmoxAPI

from .common import app_state
from .pve.schemas import PveNode, PveQemuVm
from .pve.worker import WorkerJob, create_worker
from .pve.worker import logger as worker_logger

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

worker_logger.setLevel(logging.DEBUG)


def load_config():
    app_state.config_file = os.getenv("APP_CONFIG_FILE", app_state.config_file)
    with open(app_state.config_file, "r", encoding="utf-8") as file_pointer:
        app_state.config = json.load(file_pointer)

    logger.debug("app_config")
    logger.debug(json.dumps(app_state.config, indent=2))


load_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    n_workers = app_state.config["n_workers"]
    for i in range(n_workers):
        app_state.workers.append(create_worker(app_state.queue))

    logger.debug(f"started {n_workers} workers")

    yield

    logger.debug("stopped workers ...")

    # do not call join in the first loop for a slightly quicker shutdown
    for worker in app_state.workers:
        worker.stop_requested.set()

    for worker in app_state.workers:
        worker.thread.join()

    logger.debug("stopped all workers")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/nodes")
async def get_nodes() -> list[PveNode]:
    """Cluster node index."""

    return_value = {"response": None}

    def _fetch_function(proxmox_api: ProxmoxAPI):
        logger.info(f"job running in {threading.get_ident()}")
        return_value["response"] = proxmox_api.nodes.get()

    def _get_nodes_in_worker():
        worker_job = WorkerJob(_fetch_function, threading.Event())
        app_state.queue.put(worker_job)
        worker_job.done_event.wait()
        return return_value["response"]

    nodes = await asyncio.to_thread(_get_nodes_in_worker)
    return nodes


@app.get("/nodes/{node}/vms", responses={404: {"description": "Unavailable node."}})
async def get_node_vms(
    node: Annotated[str, "The cluster node name."],
) -> list[PveQemuVm]:
    """Virtual machine index (per node)."""

    return_value = {"response": None}

    def _fetch_function(proxmox_api: ProxmoxAPI):
        logger.info(f"job running in {threading.get_ident()}")
        return_value["response"] = proxmox_api.nodes(node).qemu.get()

    def _get_node_qemu_in_worker():
        worker_job = WorkerJob(_fetch_function, threading.Event())
        app_state.queue.put(worker_job)
        worker_job.done_event.wait()
        return return_value["response"]

    node_vms = await asyncio.to_thread(_get_node_qemu_in_worker)
    return node_vms
