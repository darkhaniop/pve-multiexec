from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from ..config import settings


@dataclass
class AppState:
    config_file: str
    config: dict[str, Any]
    executor: ThreadPoolExecutor | None = None


app_state = AppState(
    config_file=settings.config_file,
    config=settings.model_dump(),
    executor=None,
)
