import logging
import os

import proxmoxer
from dotenv import load_dotenv
from proxmoxer import ProxmoxAPI

from pve_drop_guest_caches.pve.api_initializer import create_proxmox_api

load_dotenv()

# logging.basicConfig()
# proxmoxer.logger.setLevel(logging.DEBUG)


def sent_request(proxmox_api: ProxmoxAPI, node: str) -> None:
    return proxmox_api.nodes(node).status.get()


def main():
    print("quick status check")

    proxmox_api = create_proxmox_api()
    response = sent_request(proxmox_api, os.getenv("MY_PVE_NODE", ""))
    print("response:\n", response)


if __name__ == "__main__":
    main()
