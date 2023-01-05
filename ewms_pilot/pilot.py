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
from mqclient.broker_client_interface import TIMEOUT_MILLIS_DEFAULT
from wipac_dev_tools import argparse_tools, logging_tools

LOGGER = logging.getLogger("ewms-pilot")


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


async def consume_and_reply(
    cmd: str,
    #
    # for mq
    broker_client: str,
    broker_address: str,
    auth_token: str,
    #
    queue_to_clients: str,
    queue_from_clients: str,
    #
    timeout_to_clients: int = TIMEOUT_MILLIS_DEFAULT // 1000,
    timeout_from_clients: int = TIMEOUT_MILLIS_DEFAULT // 1000,
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
    """Communicate with server and outsource processing to subprocesses."""
    LOGGER.info("Making MQClient queue connections...")
    except_errors = False  # if there's an error, have the cluster try again (probably a system error)
    in_queue = mq.Queue(
        broker_client,
        address=broker_address,
        name=queue_to_clients,
        auth_token=auth_token,
        except_errors=except_errors,
        timeout=timeout_to_clients,
    )
    out_queue = mq.Queue(
        broker_client,
        address=broker_address,
        name=queue_from_clients,
        auth_token=auth_token,
        except_errors=except_errors,
        timeout=timeout_from_clients,
    )
    try:
        subproc_timeout = int(os.environ["EWMS_PILOT_SUBPROC_TIMEOUT"])  # -> ValueError
    except KeyError:
        subproc_timeout = None

    LOGGER.info("Getting messages from server to process then send back...")
    async with in_queue.open_sub() as sub, out_queue.open_pub() as pub:
        async for i, in_msg in asl.enumerate(sub):
            LOGGER.info(f"Got a message to process (#{i}): {str(in_msg)}")

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
        "--mq-basename",
        required=True,
        help="base identifier to correspond to a task for its MQ incoming & outgoing connections",
    )
    parser.add_argument(
        "--broker-client",
        default="pulsar",
        choices=["pulsar", "rabbitmq", "nats", "gcp"],
        help="which kind of broker",
    )
    parser.add_argument(
        "-b",
        "--broker",
        required=True,
        help="The MQ broker URL to connect to",
    )
    parser.add_argument(
        "-a",
        "--auth-token",
        default=None,
        help="The MQ authentication token to use",
    )
    parser.add_argument(
        "--timeout-to-clients",
        default=60 * 1,
        type=int,
        help="timeout (seconds) for messages TO client(s)",
    )
    parser.add_argument(
        "--timeout-from-clients",
        default=60 * 30,
        type=int,
        help="timeout (seconds) for messages FROM client(s)",
    )

    # logging args
    parser.add_argument(
        "-l",
        "--log",
        default="INFO",
        help="the output logging level (for first-party loggers)",
    )
    parser.add_argument(
        "--log-third-party",
        default="WARNING",
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
    LOGGER.info(f"Starting up an EWMS Pilot for MQ task: {args.mq_basename} (basename)")
    asyncio.get_event_loop().run_until_complete(
        consume_and_reply(
            cmd=args.cmd,
            broker_client=args.broker_client,
            broker_address=args.broker,
            auth_token=args.auth_token,
            queue_to_clients=f"to-clients-{args.mq_basename}",
            queue_from_clients=f"from-clients-{args.mq_basename}",
            timeout_to_clients=args.timeout_to_clients,
            timeout_from_clients=args.timeout_from_clients,
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
