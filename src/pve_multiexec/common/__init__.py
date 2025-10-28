from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from ..config import settings
from ..pve.worker import get_pve_executor


@dataclass
class AppState:
    config_file: str = settings.config_file
    config: dict[str, Any] = field(default_factory=settings.model_dump)

    @property
    def executor(self) -> ThreadPoolExecutor | None:
        return get_pve_executor()


app_state = AppState()
