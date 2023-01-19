"""API for launching an MQ-task pilot."""


import argparse
import asyncio
import enum
import json
import logging
import os
import pickle
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Optional

import asyncstdlib as asl
import mqclient as mq
from wipac_dev_tools import argparse_tools, logging_tools

from .config import ENV

LOGGER = logging.getLogger("ewms-pilot")

_DEFAULT_TIMEOUT_INCOMING = 1  # second
_DEFAULT_TIMEOUT_OUTGOING = 1  # second
_DEFAULT_PREFETCH = 1


class FileType(enum.Enum):
    """Various file types/extensions."""

    PICKLE = ".pkl"
    PLAIN_TEXT = ".txt"
    JSON = ".json"


class UniversalFileInterface:
    """Support reading and writing for any `FileType` file extension."""

    @classmethod
    def write(cls, in_msg: Any, fpath: Path) -> None:
        """Write `stuff` to `fpath` per `fpath.suffix`."""
        cls._write(in_msg, fpath)
        LOGGER.info(f"File Written :: {fpath} ({fpath.stat().st_size} bytes)")

    @classmethod
    def _write(cls, in_msg: Any, fpath: Path) -> None:
        LOGGER.info(f"Writing payload to file @ {fpath}")
        LOGGER.debug(in_msg)

        # PICKLE
        if fpath.suffix == FileType.PICKLE.value:
            with open(fpath, "wb") as f:
                pickle.dump(in_msg, f)
        # PLAIN_TEXT
        elif fpath.suffix == FileType.PLAIN_TEXT.value:
            with open(fpath, "w") as f:
                f.write(in_msg)
        # JSON
        elif fpath.suffix == FileType.JSON.value:
            with open(fpath, "w") as f:
                json.dump(in_msg, f)
        # ???
        else:
            raise ValueError(f"Unsupported file type: {fpath.suffix} ({fpath})")

    @classmethod
    def read(cls, fpath: Path) -> Any:
        """Read and return contents of `fpath` per `fpath.suffix`."""
        msg = cls._read(fpath)
        LOGGER.info(f"File Read :: {fpath} ({fpath.stat().st_size} bytes)")
        LOGGER.debug(msg)
        return msg

    @classmethod
    def _read(cls, fpath: Path) -> Any:
        LOGGER.info(f"Reading payload from file @ {fpath}")

        # PICKLE
        if fpath.suffix == FileType.PICKLE.value:
            with open(fpath, "rb") as f:
                return pickle.load(f)
        # PLAIN_TEXT
        elif fpath.suffix == FileType.PLAIN_TEXT.value:
            with open(fpath, "r") as f:
                return f.read()
        # JSON
        elif fpath.suffix == FileType.JSON.value:
            with open(fpath, "r") as f:
                return json.load(f)
        # ???
        else:
            raise ValueError(f"Unsupported file type: {fpath.suffix} ({fpath})")


def write_to_subproc(
    fpath_to_subproc: Path,
    in_msg: Any,
    debug_subdir: Optional[Path],
    file_writer: Callable[[Any, Path], None],
) -> Path:
    """Write the msg to the `IN` file.

    Also, dump to a file for debugging (if not "").
    """
    file_writer(in_msg, fpath_to_subproc)

    # persist the file?
    if debug_subdir:
        file_writer(in_msg, debug_subdir / fpath_to_subproc.name)

    return fpath_to_subproc


def read_from_subproc(
    fpath_from_subproc: Path,
    debug_subdir: Optional[Path],
    file_reader: Callable[[Path], Any],
) -> Any:
    """Read the msg from the `OUT` file.

    Also, dump to a file for debugging (if not "").
    """
    if not fpath_from_subproc.exists():
        LOGGER.error("Out file was not written for in-payload")
        raise RuntimeError("Out file was not written for in-payload")

    out_msg = file_reader(fpath_from_subproc)

    # persist the file?
    if debug_subdir:
        # fpath_from_subproc.rename(debug_subdir / fpath_from_subproc.name)  # mv
        # NOTE: https://github.com/python/cpython/pull/30650
        shutil.move(fpath_from_subproc, debug_subdir / fpath_from_subproc.name)
    else:
        fpath_from_subproc.unlink()  # rm

    return out_msg


def process_msg(
    in_msg: Any,
    cmd: str,
    subproc_timeout: Optional[int],
    fpath_to_subproc: Path,
    fpath_from_subproc: Path,
    file_writer: Callable[[Any, Path], None],
    file_reader: Callable[[Path], Any],
    debug_dir: Optional[Path],
) -> Any:
    """Process the message in a subprocess using `cmd`."""
    # debugging logic
    debug_subdir = None
    if debug_dir:
        debug_subdir = debug_dir / str(time.time())
        debug_subdir.mkdir(parents=True, exist_ok=False)

    # write
    write_to_subproc(fpath_to_subproc, in_msg, debug_subdir, file_writer)

    # call & check outputs
    LOGGER.info(f"Executing: {shlex.split(cmd)}")
    subprocess.run(
        shlex.split(cmd),
        check=True,
        timeout=subproc_timeout,
    )

    # get
    out_msg = read_from_subproc(fpath_from_subproc, debug_subdir, file_reader)
    return out_msg


async def consume_and_reply(
    cmd: str,
    #
    queue_incoming: str,
    queue_outgoing: str,
    #
    # for mq
    broker_client: str = ENV.EWMS_PILOT_BROKER_CLIENT,
    broker_address: str = ENV.EWMS_PILOT_BROKER_ADDRESS,
    auth_token: str = ENV.EWMS_PILOT_BROKER_AUTH_TOKEN,
    #
    prefetch: int = _DEFAULT_PREFETCH,
    #
    timeout_wait_for_first_message: Optional[int] = None,
    timeout_incoming: int = _DEFAULT_TIMEOUT_INCOMING,
    timeout_outgoing: int = _DEFAULT_TIMEOUT_OUTGOING,
    #
    # for subprocess
    fpath_to_subproc: Path = Path("./in.pkl"),
    fpath_from_subproc: Path = Path("./out.pkl"),
    #
    file_writer: Callable[[Any, Path], None] = UniversalFileInterface.write,
    file_reader: Callable[[Path], Any] = UniversalFileInterface.read,
    #
    debug_dir: Optional[Path] = None,
) -> None:
    """Communicate with server and outsource processing to subprocesses.

    Arguments:
        `timeout_wait_for_first_message`: if None, use 'timeout_incoming'
    """
    LOGGER.info("Making MQClient queue connections...")
    except_errors = False  # if there's an error, have the cluster try again (probably a system error)

    if not queue_incoming or not queue_outgoing:
        raise RuntimeError("Must define an incoming and an outgoing queue")

    in_queue = mq.Queue(
        broker_client,
        address=broker_address,
        name=queue_incoming,
        prefetch=prefetch,
        auth_token=auth_token,
        except_errors=except_errors,
        # timeout=timeout_incoming, # manually set below
    )
    out_queue = mq.Queue(
        broker_client,
        address=broker_address,
        name=queue_outgoing,
        auth_token=auth_token,
        except_errors=except_errors,
        timeout=timeout_outgoing,
    )
    try:
        subproc_timeout = int(os.environ["EWMS_PILOT_SUBPROC_TIMEOUT"])  # -> ValueError
    except KeyError:
        subproc_timeout = None

    LOGGER.info("Getting messages from server to process then send back...")
    async with out_queue.open_pub() as pub:

        # FIRST MESSAGE
        in_queue.timeout = (
            timeout_wait_for_first_message
            if timeout_wait_for_first_message
            else timeout_incoming
        )
        async with in_queue.open_sub_one() as in_msg:
            LOGGER.info(f"Got a message to process (#0): {str(in_msg)}")
            out_msg = process_msg(
                in_msg,
                cmd,
                subproc_timeout,
                fpath_to_subproc,
                fpath_from_subproc,
                file_writer,
                file_reader,
                debug_dir,
            )
            # send
            LOGGER.info("Sending out-payload to server...")
            await pub.send(out_msg)

        # ADDITIONAL MESSAGES
        in_queue.timeout = timeout_incoming
        async with in_queue.open_sub() as sub:
            async for i, in_msg in asl.enumerate(sub, start=1):
                LOGGER.info(f"Got a message to process (#{i}): {str(in_msg)}")
                out_msg = process_msg(
                    in_msg,
                    cmd,
                    subproc_timeout,
                    fpath_to_subproc,
                    fpath_from_subproc,
                    file_writer,
                    file_reader,
                    debug_dir,
                )
                # send
                LOGGER.info("Sending out-payload to server...")
                await pub.send(out_msg)

    # check if anything was actually processed
    try:
        n_msgs = i + 1  # 0-indexing :) # pylint: disable=undefined-loop-variable
    except NameError:
        raise RuntimeError("No Messages Were Received.")
    LOGGER.info(f"Done Processing: handled {n_msgs} messages")


def main() -> None:
    """Start up EWMS Pilot subprocess to perform an MQ task."""

    parser = argparse.ArgumentParser(
        description="Start up EWMS Pilot subprocess to perform an MQ task",
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--cmd",  # alternatively we can go with a condor-like --executable and --arguments
        required=True,
        help="the command to give the subprocess script",
    )
    parser.add_argument(
        "--in",
        dest="infile",
        default=Path("./in.pkl"),
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).suffix in [e.value for e in FileType],
            argparse.ArgumentTypeError(f"Unsupported file type: {x}"),
        ),
        help="which file to write for the client/pilot's subprocess",
    )
    parser.add_argument(
        "--out",
        dest="outfile",
        default=Path("./out.pkl"),
        type=lambda x: argparse_tools.validate_arg(
            Path(x),
            Path(x).suffix in [e.value for e in FileType],
            argparse.ArgumentTypeError(f"Unsupported file type: {x}"),
        ),
        help="which file to read from the client/pilot's subprocess",
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
        default=_DEFAULT_PREFETCH,
        type=int,
        help="prefetch for incoming messages",
    )
    parser.add_argument(
        "--timeout-wait-for-first-message",
        default=None,
        type=int,
        help="timeout (seconds) for the first message to arrive at the client(s); "
        "defaults to `--timeout-incoming` value",
    )
    parser.add_argument(
        "--timeout-incoming",
        default=_DEFAULT_TIMEOUT_INCOMING,
        type=int,
        help="timeout (seconds) for messages TO client(s)",
    )
    parser.add_argument(
        "--timeout-outgoing",
        default=_DEFAULT_TIMEOUT_OUTGOING,
        type=int,
        help="timeout (seconds) for messages FROM client(s)",
    )

    # logging args
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

    # testing/debugging args
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
            broker_client=args.broker_client,
            broker_address=args.broker,
            auth_token=args.auth_token,
            queue_incoming=args.queue_incoming,
            queue_outgoing=args.queue_outgoing,
            prefetch=args.prefetch,
            timeout_wait_for_first_message=args.timeout_wait_for_first_message,
            timeout_incoming=args.timeout_incoming,
            timeout_outgoing=args.timeout_outgoing,
            fpath_to_subproc=args.infile,
            fpath_from_subproc=args.outfile,
            debug_dir=args.debug_directory,
            # file_writer=UniversalFileInterface.write,
            # file_reader=UniversalFileInterface.read,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
