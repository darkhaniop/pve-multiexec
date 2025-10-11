import json
import logging
import os
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Proxmox VE connection settings
    pve_host: str = Field(
        default="",
        validation_alias=AliasChoices("pve_host", "my_pve_host"),
        description="Proxmox VE host/IP address.",
    )
    pve_user: str = Field(
        default="",
        validation_alias=AliasChoices("pve_user", "my_pve_user"),
        description="Proxmox VE username.",
    )
    pve_token_name: str = Field(
        default="",
        validation_alias=AliasChoices("pve_token_name", "my_pve_token_name"),
        description="Proxmox VE API Token Name.",
    )
    pve_token_uuid: str = Field(
        default="",
        validation_alias=AliasChoices("pve_token_uuid", "my_pve_token_uuid"),
        description="Proxmox VE API Token Secret / UUID.",
    )
    pve_verify_ssl: bool = Field(
        default=False,
        validation_alias=AliasChoices("pve_verify_ssl", "my_pve_verify_ssl"),
        description="Whether to verify SSL certificates when connecting to Proxmox VE.",
    )
    pve_node: str = Field(
        default="",
        validation_alias=AliasChoices("pve_node", "my_pve_node"),
        description="Default Proxmox VE cluster node name.",
    )

    # Application settings
    n_workers: int = Field(
        default=3,
        validation_alias=AliasChoices("n_workers", "my_n_workers"),
        description="Number of worker threads for Proxmox API calls.",
    )
    db_file: str = Field(
        default="database.db",
        validation_alias=AliasChoices("db_file", "my_db_file"),
        description="SQLite database file name/path.",
    )
    config_file: str = Field(
        default="config.json",
        validation_alias=AliasChoices("app_config_file", "config_file"),
        description="Optional JSON configuration file path.",
    )


def load_settings() -> Settings:
    """Load settings from optional JSON config file, environment variables, and .env."""

    config_file = os.getenv("APP_CONFIG_FILE", "config.json")
    file_settings: dict = {}
    config_path = Path(config_file)
    if config_path.is_file():
        try:
            with open(config_path, "r", encoding="utf-8") as file_pointer:
                file_settings = json.load(file_pointer)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(f"Could not read config file {config_path}: {exc}")

    return Settings(**file_settings)


settings = load_settings()
