import queue
from dataclasses import dataclass
from typing import Any

from ..pve.worker import WorkerJob, WorkerState


@dataclass
class AppState:
    config_file: str
    config: dict[str, Any]
    queue: queue.Queue[WorkerJob]
    workers: list[WorkerState]


app_state = AppState(
    config_file="config.json", config={}, queue=queue.Queue(), workers=[]
)
