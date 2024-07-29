"""Main."""

import argparse
import asyncio
import logging

from wipac_dev_tools import logging_tools

from .config import ENV
from .pilot import consume_and_reply

LOGGER = logging.getLogger(__package__)


def main() -> None:
    """Start up EWMS Pilot to do tasks, communicate via message passing."""

    parser = argparse.ArgumentParser(
        description="Start up EWMS Pilot task to perform an MQ task",
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # task definition
    parser.add_argument(
        "--task-image",
        required=True,
        help="the image build (and container to run) for each task",
    )
    parser.add_argument(
        "--task-args",
        required=True,
        help="the args to run with the task container",
    )

    # I/O config
    parser.add_argument(
        "--infile-type",
        required=True,
        help="the file type (extension) of the input file for the pilot's task",
    )
    parser.add_argument(
        "--outfile-type",
        required=True,
        help="the file type (extension) of the output file from the pilot's task",
    )

    # init definition
    parser.add_argument(
        "--init-image",
        required=True,
        help="the image build (and container to run) once before processing any tasks",
    )
    parser.add_argument(
        "--init-args",
        required=True,
        help="the args to run with the init container",
    )

    args = parser.parse_args()
    logging_tools.set_level(
        ENV.EWMS_PILOT_CL_LOG,  # type: ignore[arg-type]
        first_party_loggers=[LOGGER],
        third_party_level=ENV.EWMS_PILOT_CL_LOG_THIRD_PARTY,  # type: ignore[arg-type]
        use_coloredlogs=True,
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # GO!
    LOGGER.info(
        f"Starting up an EWMS Pilot for MQ task: {args.task_image} w/ {args.task_args}"
    )
    asyncio.run(
        consume_and_reply(
            task_image=args.task_image,
            task_args=args.task_args,
            #
            # to subprocess
            infile_type=args.infile_type,
            outfile_type=args.outfile_type,
            #
            # init
            init_image=args.init_image,
            init_args=args.init_args,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
