"""API for launching an MQ-task pilot."""


import argparse
import asyncio
import enum
import json
import pickle
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

import asyncstdlib as asl
from wipac_dev_tools import logging_tools

from . import LOGGER, mq


class FileEncoding(enum.Enum):
    """Various field extensions/encodings."""

    PICKLE = "pkl"
    PLAIN_TEXT = "txt"
    JSON = "json"
    BINARY = "bin"


class UniversalFileInterface:
    """Support reading and writing for any `FileEncoding` file extension."""

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
        if fpath.suffix == FileEncoding.PICKLE.value:
            with open(fpath, "wb") as f:
                pickle.dump(in_msg, f)
        # PLAIN_TEXT
        elif fpath.suffix == FileEncoding.PLAIN_TEXT.value:
            with open(fpath, "w") as f:
                f.write(in_msg)
        # JSON
        elif fpath.suffix == FileEncoding.JSON.value:
            with open(fpath, "w") as f:
                json.dump(in_msg, f)
        # BINARY
        elif fpath.suffix == FileEncoding.BINARY.value:
            with open(fpath, "wb") as f:
                f.write(in_msg)
        # ???
        else:
            raise ValueError(f"Unsupported file encoding: {fpath.suffix} ({fpath})")

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
        if fpath.suffix == FileEncoding.PICKLE.value:
            with open(fpath, "rb") as f:
                return pickle.load(f)
        # PLAIN_TEXT
        elif fpath.suffix == FileEncoding.PLAIN_TEXT.value:
            with open(fpath, "r") as f:
                return f.read()
        # JSON
        elif fpath.suffix == FileEncoding.JSON.value:
            with open(fpath, "r") as f:
                return json.load(f)
        # BINARY
        elif fpath.suffix == FileEncoding.BINARY.value:
            with open(fpath, "wb") as f:
                return f.read()
        # ???
        else:
            raise ValueError(f"Unsupported file encoding: {fpath.suffix} ({fpath})")


def write_to_client(
    fpath_to_client: Path,
    in_msg: Any,
    debug_subdir: Optional[Path],
    file_writer: Callable[[Any, Path], None],
) -> Path:
    """Write the msg to the `IN` file.

    Also, dump to a file for debugging (if not "").
    """
    file_writer(in_msg, fpath_to_client)

    # persist the file?
    if debug_subdir:
        file_writer(in_msg, debug_subdir / fpath_to_client.name)

    return fpath_to_client


def read_from_client(
    fpath_from_client: Path,
    debug_subdir: Optional[Path],
    file_writer: Callable[[Any, Path], None],
    file_reader: Callable[[Path], Any],
) -> Any:
    """Read the msg from the `OUT` file.

    Also, dump to a file for debugging (if not "").
    """
    if not fpath_from_client.exists():
        LOGGER.error("Out file was not written for in-payload")
        raise RuntimeError("Out file was not written for in-payload")

    out_msg = file_reader(fpath_from_client)
    fpath_from_client.unlink()  # rm

    # persist the file?
    if debug_subdir:
        file_writer(out_msg, debug_subdir / fpath_from_client.name)

    return out_msg


async def consume_and_reply(
    cmd: str,
    #
    broker: str,  # for mq
    auth_token: str,  # for mq
    queue_to_clients: str,  # for mq
    queue_from_clients: str,  # for mq
    #
    timeout_to_clients: int,  # for mq
    timeout_from_clients: int,  # for mq
    #
    fpath_to_client: Path = Path("./in.pkl"),
    fpath_from_client: Path = Path("./out.pkl"),
    #
    debug_dir: Optional[Path] = None,
    #
    file_writer: Callable[[Any, Path], None] = UniversalFileInterface.write,
    file_reader: Callable[[Path], Any] = UniversalFileInterface.read,
) -> None:
    """Communicate with server and outsource processing to subprocesses."""
    LOGGER.info("Making MQClient queue connections...")
    except_errors = False  # if there's an error, have the cluster try again (probably a system error)
    in_queue = mq.Queue(
        address=broker,
        name=queue_to_clients,
        auth_token=auth_token,
        except_errors=except_errors,
        timeout=timeout_to_clients,
    )
    out_queue = mq.Queue(
        address=broker,
        name=queue_from_clients,
        auth_token=auth_token,
        except_errors=except_errors,
        timeout=timeout_from_clients,
    )

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
            write_to_client(fpath_to_client, in_msg, debug_subdir, file_writer)

            # call & check outputs
            LOGGER.info(f"Executing: {cmd.split()}")
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                check=False,
                text=True,
            )
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, cmd.split())

            # get
            out_msg = read_from_client(
                fpath_from_client, debug_subdir, file_writer, file_reader
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

    def _create_dir(val: str) -> Optional[Path]:
        if not val:
            return None
        path = Path(val)
        path.mkdir(parents=True, exist_ok=True)
        return path

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
        "-e",
        "--encoding",
        default=FileEncoding.PICKLE.value,
        choices=[e.value for e in FileEncoding],
        help="which file encoding to use for in- & out-files",
    )

    # mq args
    parser.add_argument(
        "--mq-basename",
        required=True,
        help="base identifier to correspond to a task for its MQ incoming & outgoing connections",
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
        type=_create_dir,
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
    LOGGER.info(f"Starting up an EWMS Pilot for MQ task: {args.mq_basename=}")
    asyncio.get_event_loop().run_until_complete(
        consume_and_reply(
            cmd=args.cmd,
            broker=args.broker,
            auth_token=args.auth_token,
            queue_to_clients=f"to-clients-{args.mq_basename}",
            queue_from_clients=f"from-clients-{args.mq_basename}",
            timeout_to_clients=args.timeout_to_clients,
            timeout_from_clients=args.timeout_from_clients,
            fpath_to_client=Path(f"./in.{args.encoding}"),
            fpath_from_client=Path(f"./out.{args.encoding}"),
            debug_dir=args.debug_directory,
            # file_writer=UniversalFileInterface.write,
            # file_reader=UniversalFileInterface.read,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
