import logging

from .models import Invocation
from .utils import InvocationResult

logger = logging.getLogger(__name__)


async def run_invocation(db_invocation: Invocation) -> None:
    invocation_result = InvocationResult.model_validate(db_invocation.model_dump())
    logger.info(invocation_result.model_dump_json(indent=2))
