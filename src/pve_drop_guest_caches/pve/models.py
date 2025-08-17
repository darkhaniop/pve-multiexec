from typing import Annotated, Literal
from pydantic import BaseModel, Field

class PveNode(BaseModel):
    # Node info returned from GET /api2/json/nodes
    node: Annotated[str, Field(min_length=1, description="The cluster node name.")]
    status: Annotated[Literal["unknown", "online", "offline"], Field(description="Node status.")]

    # optional fields
    cpu: Annotated[float | None, Field(default=None, description="CPU utilization.")]
    level: Annotated[str | None, Field(default=None, description="Support level.")]
    maxcpu: Annotated[int | None, Field(default=None, description="Number of available CPUs.")]
    maxmem: Annotated[int | None, Field(default=None, description="Number of available memory in bytes.")]
    mem: Annotated[int | None, Field(default=None, description="Used memory in bytes.")]
    ssl_fingerprint: Annotated[str | None, Field(default=None, description="The SSL fingerprint for the node certificate.")]
    uptime: Annotated[int | None, Field(default=None, description="Node uptime in seconds.")]
    
class PveQemuVm(BaseModel):
    # VM info returned from GET /api2/json/nodes/{node}/qemu
    status: Annotated[Literal["stopped", "running"], Field(description="QEMU process status.")]
    vmid: Annotated[int, Field(ge=100, le=999999999, description="The (unique) ID of the VM.")]

    # optional fields
    cpu: Annotated[float | None, Field(default=None, description="Current CPU usage.")]
    cpus: Annotated[float | None, Field(default=None, description="Maximum usable CPUs.")]
    diskread: Annotated[int | None, Field(default=None, description="The amount of bytes the guest read from it's block devices since the guest was started. (Note: This info is not available for all storage types.)")]
    diskwrite: Annotated[int | None, Field(default=None, description="The amount of bytes the guest wrote from it's block devices since the guest was started. (Note: This info is not available for all storage types.)")]
    lock: Annotated[str | None, Field(default=None, description="The current config lock, if any.")]
    maxdisk: Annotated[int | None, Field(default=None, description="Root disk size in bytes.")]
    maxmem: Annotated[int | None, Field(default=None, description="Maximum memory in bytes.")]
    mem: Annotated[int | None, Field(default=None, description="Currently used memory in bytes.")]
    name: Annotated[str | None, Field(default=None, description="VM (host)name.")]
    netin: Annotated[int | None, Field(default=None, description="The amount of traffic in bytes that was sent to the guest over the network since it was started.")]
    netout: Annotated[float | None, Field(default=None, description="The amount of traffic in bytes that was sent from the guest over the network since it was started.")]
    pid: Annotated[float | None, Field(default=None, description="PID of the QEMU process, if the VM is running.")]
    qmpstatus: Annotated[float | None, Field(default=None, description="VM run state from the 'query-status' QMP monitor command.")]
    running_machine: Annotated[float | None, Field(default=None, alias="running-machine", description="The currently running machine type (if running).")]
    running_qemu: Annotated[float | None, Field(default=None, alias="running-qemu", description="The QEMU version the VM is currently using (if running).")]
    serial: Annotated[bool | None, Field(default=None, description="Guest has serial device configured.")]
    tags: Annotated[str | None, Field(default=None, description="The current configured tags, if any")]
    template: Annotated[bool, Field(default=False, description="Determines if the guest is a template.")]
    uptime: Annotated[int | None, Field(default=None, description="Uptime in seconds.")]
