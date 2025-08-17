from typing import Annotated
import asyncio
from fastapi import FastAPI

from .pve.api_initializer import create_proxmox_api
from .pve.models import PveNode, PveQemuVm


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/nodes")
async def get_nodes() -> list[PveNode]:
    """Cluster node index."""

    def _get_nodes_in_worker():
        pve_api = create_proxmox_api()
        return pve_api.nodes.get()

    nodes = await asyncio.to_thread(_get_nodes_in_worker)
    return nodes


@app.get("/nodes/{node}/vms", responses={404: {"description": "Unavailable node."}})
async def get_node_vms(node: Annotated[str, "The cluster node name."]) -> list[PveQemuVm]:
    """Virtual machine index (per node)."""

    def _get_node_qemu_in_worker():
        pve_api = create_proxmox_api()
        return pve_api.nodes(node).qemu.get()

    node_vms = await asyncio.to_thread(_get_node_qemu_in_worker)
    return node_vms
