from proxmoxer import ProxmoxAPI

from ..config import settings


def create_proxmox_api() -> ProxmoxAPI:
    pve_host = settings.pve_host
    pve_user = settings.pve_user
    pve_token_name = settings.pve_token_name
    pve_token_secret = settings.pve_token_uuid
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
        verify_ssl=settings.pve_verify_ssl,
    )
