"""Main."""


import argparse
import asyncio

from wipac_dev_tools import argparse_tools, logging_tools

from .config import DEFAULT_TIMEOUT_INCOMING, DEFAULT_TIMEOUT_OUTGOING, ENV, LOGGER
from .pilot import consume_and_reply
from .tasks.io import FileType


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
        type=FileType,
        required=True,
        help="the file type (extension) of the input file for the pilot's task",
    )
    parser.add_argument(
        "--outfile-type",
        type=FileType,
        required=True,
        help="the file type (extension) of the output file from the pilot's task",
    )
    parser.add_argument(
        "--init-cmd",  # alternatively we can go with a condor-like --executable and --arguments
        default="",
        help="the init command run once before processing any tasks",
    )
    parser.add_argument(
        "--multitasking",
        type=int,
        default=ENV.EWMS_PILOT_CONCURRENT_TASKS,
        help="the max number of tasks to process in parallel",
    )

    # mq args
    parser.add_argument(
        "--queue-incoming",
        required=True,
        help="the name of the incoming queue",
    )
    parser.add_argument(
        "--queue-outgoing",
        required=True,
        help="the name of the outgoing queue",
    )
    parser.add_argument(
        "--broker-client",
        default=ENV.EWMS_PILOT_BROKER_CLIENT,
        help="which kind of broker: pulsar, rabbitmq, etc.",
    )
    parser.add_argument(
        "-b",
        "--broker",
        default=ENV.EWMS_PILOT_BROKER_ADDRESS,
        help="The MQ broker URL to connect to",
    )
    parser.add_argument(
        "-a",
        "--auth-token",
        default=ENV.EWMS_PILOT_BROKER_AUTH_TOKEN,
        help="The MQ authentication token to use",
    )
    parser.add_argument(
        "--prefetch",
        default=ENV.EWMS_PILOT_PREFETCH,
        type=int,
        help="prefetch for incoming messages",
    )
    parser.add_argument(
        "--timeout-wait-for-first-message",
        default=None,
        type=int,
        help="timeout (seconds) for the first message to arrive at the pilot; "
        "defaults to `--timeout-incoming` value",
    )
    parser.add_argument(
        "--timeout-incoming",
        default=DEFAULT_TIMEOUT_INCOMING,
        type=int,
        help="timeout (seconds) for messages TO pilot",
    )
    parser.add_argument(
        "--timeout-outgoing",
        default=DEFAULT_TIMEOUT_OUTGOING,
        type=int,
        help="timeout (seconds) for messages FROM pilot",
    )

    # meta timeouts
    parser.add_argument(
        "--init-timeout",
        default=ENV.EWMS_PILOT_INIT_TIMEOUT,
        type=int,
        help="timeout (seconds) for the init command",
    )
    parser.add_argument(
        "--task-timeout",
        default=ENV.EWMS_PILOT_TASK_TIMEOUT,
        type=int,
        help="timeout (seconds) for each task",
    )
    parser.add_argument(
        "--quarantine-time",
        default=ENV.EWMS_PILOT_QUARANTINE_TIME,
        type=int,
        help="amount of time to sleep after error (useful for preventing blackhole scenarios on condor)",
    )

    # logging/debugging args
    parser.add_argument(
        "-l",
        "--log",
        default=ENV.EWMS_PILOT_LOG,
        help="the output logging level (for first-party loggers)",
    )
    parser.add_argument(
        "--log-third-party",
        default=ENV.EWMS_PILOT_LOG_THIRD_PARTY,
        help="the output logging level for third-party loggers",
    )
    parser.add_argument(
        "--dump-task-output",
        default=ENV.EWMS_PILOT_DUMP_TASK_OUTPUT,
        action="store_true",
        help="dump each task's stderr to stderr and stdout to stdout",
    )
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
            queue_incoming=args.queue_incoming,
            queue_outgoing=args.queue_outgoing,
            #
            ftype_to_subproc=args.infile_type,
            ftype_from_subproc=args.outfile_type,
            #
            init_cmd=args.init_cmd,
            #
            broker_client=args.broker_client,
            broker_address=args.broker,
            auth_token=args.auth_token,
            #
            prefetch=args.prefetch,
            #
            timeout_wait_for_first_message=args.timeout_wait_for_first_message,
            timeout_incoming=args.timeout_incoming,
            timeout_outgoing=args.timeout_outgoing,
            #
            # file_writer=UniversalFileInterface.write,
            # file_reader=UniversalFileInterface.read,
            #
            debug_dir=args.debug_directory,
            #
            init_timeout=args.init_timeout,
            task_timeout=args.task_timeout,
            quarantine_time=args.quarantine_time,
            #
            multitasking=args.multitasking,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
