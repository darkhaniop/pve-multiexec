import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException

from .api_cmd_templates.router import (
    router as cmd_templates_router,
)
from .api_exec_configs.router import (
    router as exec_configs_router,
)
from .api_invocations.background import logger as background_logger
from .api_invocations.router import router as invocations_router
from .common import app_state
from .config import settings
from .db import db_init
from .pve.schemas import PveNode, PveQemuVm
from .pve.worker import create_worker, run_in_pve_worker
from .pve.worker import logger as worker_logger

logging.basicConfig()
logger = logging.getLogger(__name__)

logger.setLevel(logging.DEBUG)
worker_logger.setLevel(logging.INFO)
background_logger.setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_init()

    n_workers = settings.n_workers
    for _ in range(n_workers):
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
    try:
        nodes = await run_in_pve_worker(app_state.queue, lambda api: api.nodes.get())
        return nodes
    except Exception as exc:
        logger.error(f"Error fetching cluster nodes: {exc}")
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch nodes from Proxmox VE: {exc}"
        ) from exc


@app.get("/nodes/{node}/vms", responses={404: {"description": "Unavailable node."}})
async def get_node_vms(
    node: Annotated[str, "The cluster node name."],
) -> list[PveQemuVm]:
    """Virtual machine index (per node)."""
    try:
        node_vms = await run_in_pve_worker(
            app_state.queue, lambda api, n: api.nodes(n).qemu.get(), [node]
        )
        return node_vms
    except Exception as exc:
        logger.error(f"Error fetching VMs for node {node}: {exc}")
        raise HTTPException(
            status_code=404, detail=f"Node '{node}' not found or unavailable"
        ) from exc


app.include_router(
    cmd_templates_router, prefix="/cmd_templates", tags=["cmd_templates"]
)
app.include_router(exec_configs_router, prefix="/exec_configs", tags=["exec_configs"])
app.include_router(invocations_router, prefix="/invocations", tags=["invocations"])
