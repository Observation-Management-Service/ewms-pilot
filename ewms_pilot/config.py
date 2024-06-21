"""Configuration constants."""

import dataclasses as dc
import logging
import os
from typing import Optional

from wipac_dev_tools import from_environment_as_dataclass

LOGGER = logging.getLogger("ewms-pilot")


REFRESH_INTERVAL = 1  # sec -- the time between transitioning phases of the main loop


#
# Env var constants: set as constants & typecast
#


@dc.dataclass(frozen=True)
class EnvConfig:
    """For storing environment variables, typed."""

    # incoming queue
    EWMS_PILOT_QUEUE_INCOMING: str = ""  # name of the incoming queue
    EWMS_PILOT_QUEUE_INCOMING_AUTH_TOKEN: str = ""  # auth token for queue
    EWMS_PILOT_QUEUE_INCOMING_BROKER_TYPE: str = ""  # broker type: pulsar, rabbitmq...
    EWMS_PILOT_QUEUE_INCOMING_BROKER_ADDRESS: str = ""  # MQ broker URL to connect to

    # incoming queue - settings
    EWMS_PILOT_PREFETCH: int = (
        1  # prefetch amount for incoming messages (off by default -- prefetch is an optimization)
    )
    EWMS_PILOT_TIMEOUT_QUEUE_WAIT_FOR_FIRST_MESSAGE: Optional[int] = (
        None  # timeout (sec) for the first message to arrive at the pilot (defaults to incoming timeout value)
    )
    EWMS_PILOT_TIMEOUT_QUEUE_INCOMING: int = 1  # timeout (sec) for messages TO pilot

    # outgoing queue
    EWMS_PILOT_QUEUE_OUTGOING: str = ""  # name of the outgoing queue
    EWMS_PILOT_QUEUE_OUTGOING_AUTH_TOKEN: str = ""  # auth token for queue
    EWMS_PILOT_QUEUE_OUTGOING_BROKER_TYPE: str = ""  # broker type: pulsar, rabbitmq...
    EWMS_PILOT_QUEUE_OUTGOING_BROKER_ADDRESS: str = ""  # MQ broker URL to connect to

    # logging -- only used when running via command line
    EWMS_PILOT_CL_LOG: str = "INFO"  # level for 1st-party loggers
    EWMS_PILOT_CL_LOG_THIRD_PARTY: str = "WARNING"  # level for 3rd-party loggers

    # chirp
    EWMS_PILOT_HTCHIRP: bool = False
    EWMS_PILOT_HTCHIRP_DEST: str = "JOB_ATTR"  # ["JOB_EVENT_LOG", "JOB_ATTR"]
    EWMS_PILOT_HTCHIRP_RATELIMIT_INTERVAL: float = 60.0

    # timing config -- tasks
    EWMS_PILOT_INIT_TIMEOUT: Optional[int] = None  # timeout (sec) for the init command
    EWMS_PILOT_TASK_TIMEOUT: Optional[int] = None  # timeout (sec) for each task

    # task handling logic
    EWMS_PILOT_STOP_LISTENING_ON_TASK_ERROR: bool = (
        True
        # whether to stop taking future tasks after a task fails;
        # ex: set to False if on known good compute node (testing cluster),
        #     set to True  if on unknown node (large homogeneous cluster)
    )
    EWMS_PILOT_MAX_CONCURRENT_TASKS: int = 1  # max no. of tasks to process in parallel

    # misc settings
    EWMS_PILOT_DUMP_TASK_OUTPUT: bool = (
        False  # dump each task's stderr to stderr and stdout to stdout
    )
    EWMS_PILOT_QUARANTINE_TIME: int = (
        0  # how long to sleep after error (useful for preventing blackhole scenarios on condor)
    )

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

        if self.EWMS_PILOT_MAX_CONCURRENT_TASKS < 1:
            LOGGER.warning(
                f"Invalid value for 'EWMS_PILOT_MAX_CONCURRENT_TASKS' ({self.EWMS_PILOT_MAX_CONCURRENT_TASKS}),"
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
