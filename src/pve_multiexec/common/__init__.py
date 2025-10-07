import queue
from dataclasses import dataclass
from typing import Any

from ..config import settings
from ..pve.worker import WorkerJob, WorkerState


@dataclass
class AppState:
    config_file: str
    config: dict[str, Any]
    queue: queue.Queue[WorkerJob]
    workers: list[WorkerState]


app_state = AppState(
    config_file=settings.config_file,
    config=settings.model_dump(),
    queue=queue.Queue(),
    workers=[],
)
