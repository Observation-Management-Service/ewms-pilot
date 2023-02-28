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
    EWMS_PILOT_BROKER_CLIENT: str = "rabbitmq"
    EWMS_PILOT_BROKER_ADDRESS: str = "localhost"
    EWMS_PILOT_BROKER_AUTH_TOKEN: str = ""

    # logging
    EWMS_PILOT_LOG: str = "INFO"
    EWMS_PILOT_LOG_THIRD_PARTY: str = "WARNING"

    # meta
    EWMS_PILOT_SUBPROC_TIMEOUT: Optional[int] = None
    EWMS_PILOT_QUARANTINE_TIME: int = 0  # seconds


ENV = from_environment_as_dataclass(EnvConfig)
