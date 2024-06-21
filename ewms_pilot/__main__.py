"""Main."""

import argparse
import asyncio

from wipac_dev_tools import argparse_tools, logging_tools

from .config import LOGGER
from .pilot import consume_and_reply


def main() -> None:
    """Start up EWMS Pilot to do tasks, communicate via message passing."""

    parser = argparse.ArgumentParser(
        description="Start up EWMS Pilot task to perform an MQ task",
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--cmd",  # alternatively we can go with a condor-like --executable and --arguments
        required=True,
        help="the command to run for each task",
    )
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
    parser.add_argument(
        "--init-cmd",  # alternatively we can go with a condor-like --executable and --arguments
        default="",
        help="the init command run once before processing any tasks",
    )

    # logging/debugging args
    parser.add_argument(
        "--debug-directory",
        default="",
        type=argparse_tools.create_dir,
        help="a directory to write all the incoming/outgoing .pkl files "
        "(useful for debugging)",
    )

    args = parser.parse_args()
    logging_tools.set_level(
        args.log.upper(),
        first_party_loggers=[LOGGER],
        third_party_level=args.log_third_party,
        use_coloredlogs=True,
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # GO!
    LOGGER.info(
        f"Starting up an EWMS Pilot for MQ task: {args.queue_incoming} -> {args.queue_outgoing}"
    )
    asyncio.run(
        consume_and_reply(
            cmd=args.cmd,
            #
            # to subprocess
            infile_type=args.infile_type,
            outfile_type=args.outfile_type,
            #
            # init
            init_cmd=args.init_cmd,
            #
            # misc settings
            debug_dir=args.debug_directory,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
