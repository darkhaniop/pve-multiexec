"""
Workers will be used to keep connections open with "keep-alive" to allow reusing of the
same connections for consequent requests. Under the hood, proxmoxer uses the requests
library that supports "keep-alive" out-of-the-box, so by reusing a ProxmoxAPI instance,
we should be able to reuse the connections.
"""

import asyncio
import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from proxmoxer import ProxmoxAPI

from .api_initializer import create_proxmox_api


@dataclass
class WorkerJob:
    func: Callable[[ProxmoxAPI], Any]
    done_event: threading.Event
    exc: Exception | None = None


@dataclass
class WorkerState:
    stop_requested: threading.Event
    queue: queue.Queue[WorkerJob]
    thread: threading.Thread
    jobs_done: int = 0
    tick: int = 0


logger = logging.getLogger(__name__)


def _run_worker(state: WorkerState) -> None:
    ident = threading.get_ident()
    logger.debug(f"worker-{ident}: ...")

    proxmox_api = create_proxmox_api()

    while not state.stop_requested.is_set():
        state.tick += 1
        if state.tick % 20 == 0:
            logger.debug(f"worker-{ident}: tick {state.tick}")
        try:
            job = state.queue.get(timeout=0.2)
            logger.debug(f"worker-{ident}: job ...")
            try:
                job.func(proxmox_api)
            except Exception as exc:
                logger.exception(f"worker-{ident}: job failed with exception")
                job.exc = exc
            finally:
                job.done_event.set()
            state.jobs_done += 1
            logger.debug(f"worker-{ident}: job done (total: {state.jobs_done})")
        except queue.Empty:
            pass

    logger.debug(f"worker-{ident}: done")


def create_worker(queue: queue.Queue) -> WorkerState:
    worker_state = WorkerState(
        stop_requested=threading.Event(), queue=queue, thread=threading.Thread()
    )

    thread = threading.Thread(target=_run_worker, kwargs={"state": worker_state})
    worker_state.thread = thread

    thread.start()

    return worker_state


@dataclass
class _JobResult:
    result: Any = None


async def run_in_pve_worker(
    job_queue: queue.Queue,
    func: Callable[..., Any],
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> Any:
    job_result = _JobResult()

    if args is None:
        args = []

    if kwargs is None:
        kwargs = {}

    def wrapper(proxmox_api: ProxmoxAPI) -> None:
        job_result.result = func(proxmox_api, *args, **kwargs)

    worker_job = WorkerJob(wrapper, threading.Event())
    job_queue.put(worker_job)

    while not worker_job.done_event.is_set():
        await asyncio.sleep(0.1)

    if worker_job.exc is not None:
        raise worker_job.exc

    return job_result.result
