"""Main."""

import asyncio
import logging

from wipac_dev_tools import logging_tools

from .config import ENV
from .pilot import consume_and_reply

LOGGER = logging.getLogger(__package__)  # for __main__ use instead of __name__


def main() -> None:
    """Start up EWMS Pilot to do tasks, communicate via message passing."""

    logging_tools.set_level(
        ENV.EWMS_PILOT_CL_LOG,  # type: ignore[arg-type]
        first_party_loggers=__package__.split(".", maxsplit=1)[0],
        third_party_level=ENV.EWMS_PILOT_CL_LOG_THIRD_PARTY,  # type: ignore[arg-type]
        use_coloredlogs=True,
    )

    # GO!
    LOGGER.info("Running from CL: starting up an EWMS Pilot...")
    asyncio.run(consume_and_reply())
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
