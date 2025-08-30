import queue
import threading
import time
import logging


from pve_drop_guest_caches.pve.worker import create_worker


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def main():
    logger.debug("main: check worker ticks")

    dummy_queue = queue.Queue()

    ident = threading.get_ident()
    logger.debug(f"main (thread-{ident}): ...")

    worker = create_worker(dummy_queue)
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass

    worker.stop_requested.set()
    worker.thread.join()

    logger.debug(f"main (thread-{ident}): done")


if __name__ == "__main__":
    main()