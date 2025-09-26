import logging
import queue
import threading
import time

from proxmoxer import ProxmoxAPI

import pve_multiexec.pve.worker
from pve_multiexec.pve.worker import WorkerJob, create_worker

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

worker_logger = logging.getLogger(pve_multiexec.pve.worker.__name__)
worker_logger.setLevel(logging.DEBUG)


def func1(proxmox_api: ProxmoxAPI) -> None:
    logger.debug("pretend to use proxmox api")
    time.sleep(2)


def main():
    logger.debug("main: check worker ticks")

    queue1: queue.Queue[WorkerJob] = queue.Queue()

    ident = threading.get_ident()
    logger.debug(f"main (thread-{ident}): ...")

    worker = create_worker(queue1)

    job1 = WorkerJob(func1, threading.Event())
    job2 = WorkerJob(func1, threading.Event())

    time.sleep(1)
    queue1.put(job1)
    queue1.put(job2)
    start_time = time.monotonic()
    logger.debug(f"main (thread-{ident}): jobs submitted {start_time}")

    try:
        while not job2.done_event.is_set():
            time.sleep(0.2)
        if job2.done_event.is_set():
            end_time = time.monotonic()
            msg = (
                f"main (thread-{ident}): job2 done {end_time}"
                f" (duration: {end_time - start_time})"
            )
            logger.debug(msg)
    except KeyboardInterrupt:
        pass

    worker.stop_requested.set()
    worker.thread.join()

    logger.debug(f"main (thread-{ident}): done")


if __name__ == "__main__":
    main()
