"""Configuration constants."""

import dataclasses as dc

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


ENV = from_environment_as_dataclass(EnvConfig)
