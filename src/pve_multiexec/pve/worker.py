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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from proxmoxer import ProxmoxAPI

from .api_initializer import create_proxmox_api

logger = logging.getLogger(__name__)

_thread_local = threading.local()


def get_thread_proxmox_api() -> ProxmoxAPI:
    """Get or lazily initialize the ProxmoxAPI instance for the current thread.

    Maintains HTTP keep-alive connection reuse per worker thread.
    """
    if not hasattr(_thread_local, "proxmox_api"):
        _thread_local.proxmox_api = create_proxmox_api()
    return _thread_local.proxmox_api


def _execute_in_worker(
    func: Callable[..., Any], args: list[Any], kwargs: dict[str, Any]
) -> Any:
    ident = threading.get_ident()
    logger.debug(f"job running in {ident}")
    api = get_thread_proxmox_api()
    return func(api, *args, **kwargs)


async def run_in_pve_worker(
    func: Callable[..., Any],
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    executor: ThreadPoolExecutor | None = None,
) -> Any:
    """Execute a synchronous ProxmoxAPI function inside the worker thread pool."""
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    from ..common import app_state

    pool: ThreadPoolExecutor | None = executor or getattr(app_state, "executor", None)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(pool, _execute_in_worker, func, args, kwargs)


# Backward compatibility classes & functions
@dataclass
class WorkerJob:
    func: Callable[[ProxmoxAPI], Any]
    done_event: threading.Event | None = None
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
    proxmox_api = create_proxmox_api()

    while not state.stop_requested.is_set():
        state.tick += 1
        if state.tick % 20 == 0:
            logger.debug(f"worker-{ident}: tick {state.tick}")
        try:
            job = state.queue.get(timeout=0.2)
            logger.debug(f"job running in {ident}")
            try:
                job.func(proxmox_api)
            except Exception as exc:
                logger.exception(f"worker-{ident}: job failed with exception")
                job.exc = exc
            finally:
                if job.done_event is not None:
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
