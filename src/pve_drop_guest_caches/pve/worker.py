"""
Workers will be used to keep connections open with "keep-alive" to allow reusing of the
same connections for consequent requests. Under the hood, proxmoxer uses the requests
library that supports "keep-alive" out-of-the-box, so by reusing a ProxmoxAPI instance,
we should be able to reuse the connections.
"""

from proxmoxer import ProxmoxAPI
from dataclasses import dataclass
import queue
import threading
import time
from typing import Callable
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class WorkerJob:
    func: Callable[[ProxmoxAPI], bool]
    done_event: threading.Event
    exc: Exception | None = None


@dataclass
class WorkerState:
    stop_requested: threading.Event
    queue: queue.Queue[WorkerJob]
    thread: threading.Thread
    jobs_done: int = 0
    tick: int = 0


def _run_worker(state: WorkerState) -> None:
    ident = threading.get_ident()
    logger.debug(f"worker-{ident}: ...")

    while not state.stop_requested.is_set():
        time.sleep(0.2)
        state.tick += 1
        if state.tick % 20 == 0:
            logger.debug(f"worker-{ident}: tick {state.tick}")

    logger.debug(f"worker-{ident}: done")


def create_worker(queue: queue.Queue) -> WorkerState:
    worker_state = WorkerState(stop_requested=threading.Event(), queue=queue, thread=threading.Thread())

    thread = threading.Thread(target=_run_worker, kwargs={"state": worker_state})
    worker_state.thread = thread

    thread.start()

    return worker_state