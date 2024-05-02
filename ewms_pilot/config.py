"""Configuration constants."""


# pylint:disable=invalid-name

import dataclasses as dc
import logging
import os
from typing import Optional

from wipac_dev_tools import from_environment_as_dataclass

LOGGER = logging.getLogger("ewms-pilot")


REFRESH_INTERVAL = 1  # sec -- the time between transitioning phases of the main loop

DEFAULT_TIMEOUT_INCOMING = 1  # second
DEFAULT_TIMEOUT_OUTGOING = 1  # second


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
    EWMS_PILOT_QUEUE_INCOMING: str = ""
    EWMS_PILOT_QUEUE_OUTGOING: str = ""

    # logging
    EWMS_PILOT_CL_LOG: str = "INFO"  # only used when running via command line
    EWMS_PILOT_CL_LOG_THIRD_PARTY: str = "WARNING"  # ^^^
    EWMS_PILOT_DUMP_TASK_OUTPUT: bool = False

    # chirp
    EWMS_PILOT_HTCHIRP: bool = False
    EWMS_PILOT_HTCHIRP_DEST: str = "JOB_ATTR"  # ["JOB_EVENT_LOG", "JOB_ATTR"]
    EWMS_PILOT_HTCHIRP_RATELIMIT_INTERVAL: float = 60.0

    # meta
    EWMS_PILOT_INIT_TIMEOUT: Optional[int] = None
    EWMS_PILOT_TASK_TIMEOUT: Optional[int] = None
    EWMS_PILOT_STOP_LISTENING_ON_TASK_ERROR: bool = True
    EWMS_PILOT_QUARANTINE_TIME: int = 0  # seconds
    EWMS_PILOT_CONCURRENT_TASKS: int = 1
    EWMS_PILOT_PREFETCH: int = 1  # off by default -- prefetch is an optimization

    def __post_init__(self) -> None:
        if timeout := os.getenv("EWMS_PILOT_SUBPROC_TIMEOUT"):
            LOGGER.warning(
                "Using 'EWMS_PILOT_SUBPROC_TIMEOUT'; 'EWMS_PILOT_TASK_TIMEOUT' is preferred."
            )
            if self.EWMS_PILOT_TASK_TIMEOUT is not None:
                LOGGER.warning(
                    "Ignoring 'EWMS_PILOT_SUBPROC_TIMEOUT' since 'EWMS_PILOT_TASK_TIMEOUT' was provided."
                )
            else:
                # b/c frozen
                object.__setattr__(self, "EWMS_PILOT_TASK_TIMEOUT", int(timeout))

        if self.EWMS_PILOT_CONCURRENT_TASKS < 1:
            LOGGER.warning(
                f"Invalid value for 'EWMS_PILOT_CONCURRENT_TASKS' ({self.EWMS_PILOT_CONCURRENT_TASKS}),"
                " defaulting to '1'."
            )
            object.__setattr__(self, "EWMS_PILOT_CONCURRENT_TASKS", 1)  # b/c frozen

        if (
            self.EWMS_PILOT_QUARANTINE_TIME
            and not self.EWMS_PILOT_STOP_LISTENING_ON_TASK_ERROR
        ):
            raise RuntimeError(
                f"Cannot define 'EWMS_PILOT_QUARANTINE_TIME' while "
                f"'EWMS_PILOT_STOP_LISTENING_ON_TASK_ERROR' is "
                f"'{self.EWMS_PILOT_STOP_LISTENING_ON_TASK_ERROR}'"
            )

        if self.EWMS_PILOT_HTCHIRP_DEST not in ["JOB_EVENT_LOG", "JOB_ATTR"]:
            raise RuntimeError(
                f"Invalid EWMS_PILOT_HTCHIRP_DEST: {self.EWMS_PILOT_HTCHIRP_DEST}"
            )


ENV = from_environment_as_dataclass(EnvConfig)
