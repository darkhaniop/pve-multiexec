import os

from dotenv import load_dotenv
from proxmoxer import ProxmoxAPI

load_dotenv()


def create_proxmox_api() -> ProxmoxAPI:
    pve_host = os.getenv("MY_PVE_HOST")
    print(f"pve_host={pve_host}")
    pve_user = os.getenv("MY_PVE_USER")
    pve_token_name = os.getenv("MY_PVE_TOKEN_NAME")
    pve_token_secret = os.getenv("MY_PVE_TOKEN_UUID")
    if not (pve_host and pve_user and pve_token_name and pve_token_secret):
        raise ValueError("""
        Must provide env vars:
            MY_PVE_HOST
            MY_PVE_USER
            MY_PVE_TOKEN_NAME
            MY_PVE_TOKEN_UUID
        """)

    return ProxmoxAPI(
        host=pve_host,
        user=pve_user,
        token_name=pve_token_name,
        token_value=pve_token_secret,
        verify_ssl=False,
    )
