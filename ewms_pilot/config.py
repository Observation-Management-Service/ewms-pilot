"""Configuration constants."""

import dataclasses as dc
from typing import Optional

from wipac_dev_tools import from_environment_as_dataclass

# pylint:disable=invalid-name

#
# Env var constants: set as constants & typecast
#


@dc.dataclass(frozen=True)
class EnvConfig:
    """For storing environment variables, typed."""

    # broker -- assumes one broker is the norm
    EWMS_PILOT_BROKER_CLIENT: str = "pulsar"
    EWMS_PILOT_BROKER_ADDRESS: str = "localhost"
    EWMS_PILOT_BROKER_AUTH_TOKEN: str = ""

    # queues
    EWMS_PILOT_QUEUE_INCOMING: str = ""
    EWMS_PILOT_QUEUE_OUTGOING: str = ""

    # misc config
    EWMS_PILOT_PREFETCH: int = 1  # incoming messages

    # timeouts
    EWMS_PILOT_TIMEOUT_INCOMING: int = 1 * 60
    EWMS_PILOT_TIMEOUT_OUTGOING: int = 1 * 60
    EWMS_PILOT_TIMEOUT_WAIT_FOR_FIRST_MESSAGE: Optional[int] = None

    # logging
    EWMS_PILOT_LOG: str = "INFO"
    EWMS_PILOT_LOG_THIRD_PARTY: str = "WARNING"


ENV = from_environment_as_dataclass(EnvConfig)
