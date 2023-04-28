"""Configuration constants."""

# pylint:disable=invalid-name

import dataclasses as dc
import logging
import os
from typing import Optional

from wipac_dev_tools import from_environment_as_dataclass

LOGGER = logging.getLogger("ewms-pilot")


#
# Env var constants: set as constants & typecast
#


@dc.dataclass(frozen=True)
class EnvConfig:
    """For storing environment variables, typed."""

    # broker -- assumes one broker is the norm
    EWMS_PILOT_BROKER_CLIENT: str = "rabbitmq"
    EWMS_PILOT_BROKER_ADDRESS: str = "localhost"
    EWMS_PILOT_BROKER_AUTH_TOKEN: str = ""

    # logging
    EWMS_PILOT_LOG: str = "INFO"
    EWMS_PILOT_LOG_THIRD_PARTY: str = "WARNING"

    # meta
    EWMS_PILOT_TASK_TIMEOUT: Optional[int] = None
    EWMS_PILOT_QUARANTINE_TIME: int = 0  # seconds

    def __post_init__(self) -> None:
        if (
            timeout := os.getenv("EWMS_PILOT_SUBPROC_TIMEOUT")
            and self.EWMS_PILOT_TASK_TIMEOUT is None
        ):
            LOGGER.warning(
                "Using 'EWMS_PILOT_SUBPROC_TIMEOUT', 'EWMS_PILOT_TASK_TIMEOUT  is preferred."
            )
            object.__setattr__(self, "EWMS_PILOT_TASK_TIMEOUT", timeout)  # b/c frozen


ENV = from_environment_as_dataclass(EnvConfig)
