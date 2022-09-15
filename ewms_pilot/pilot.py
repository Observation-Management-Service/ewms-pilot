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
from typing import Any, Optional

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
    """ """

    def write(self, in_msg: Any, fpath: Path) -> None:
        """Write `stuff` to `fpath` per `fpath.suffix`."""
        self._write(in_msg, fpath)
        LOGGER.info(f"File Written :: {fpath} ({fpath.stat().st_size} bytes)")

    def _write(self, in_msg: Any, fpath: Path) -> None:
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

    def read_rm(self, fpath: Path) -> Any:
        """Read and return contents of `fpath` per `fpath.suffix`, then rm the file."""
        msg = self.read(fpath)
        msg.unlink()
        return msg

    def read(self, fpath: Path) -> Any:
        """Read and return contents of `fpath` per `fpath.suffix`."""
        msg = self._read(fpath)
        LOGGER.info(f"File Read :: {fpath} ({fpath.stat().st_size} bytes)")
        LOGGER.debug(msg)
        return msg

    def _read(self, fpath: Path) -> Any:
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


def inmsg_to_infile(
    in_msg_path: Path, in_msg: Any, debug_infile: Optional[Path]
) -> Path:
    """Write the msg to the `IN` file.

    Also, dump to a file for debugging (if not "").
    """
    UniversalFileInterface().write(in_msg, in_msg_path)

    if debug_infile:  # for debugging
        UniversalFileInterface().write(in_msg, debug_infile)

    return in_msg_path


def outfile_to_outmsg(out_msg_path: Path, debug_outfile: Optional[Path]) -> Any:
    """Read the msg from the `OUT` file.

    Also, dump to a file for debugging (if not "").
    """
    if not out_msg_path.exists():
        LOGGER.error("Out file was not written for in-payload")
        raise RuntimeError("Out file was not written for in-payload")

    out_msg = UniversalFileInterface().read_rm(out_msg_path)

    if debug_outfile:  # for debugging
        UniversalFileInterface().write(out_msg, debug_outfile)

    return out_msg


async def consume_and_reply(
    cmd: str,
    broker: str,  # for mq
    auth_token: str,  # for mq
    queue_to_clients: str,  # for mq
    queue_from_clients: str,  # for mq
    timeout_to_clients: int,  # for mq
    timeout_from_clients: int,  # for mq
    file_encoding: FileEncoding = FileEncoding.PICKLE,
    debug_dir: Optional[Path] = None,
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
            debug_infile, debug_outfile = None, None
            if debug_dir:
                debug_time = time.time()
                debug_infile = debug_dir / f"{debug_time}.in.{file_encoding.value}"
                debug_outfile = debug_dir / f"{debug_time}.out.{file_encoding.value}"

            # write
            inmsg_to_infile(
                Path(f"./in_msg.{file_encoding.value}"), in_msg, debug_infile
            )

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
            out_msg = outfile_to_outmsg(
                Path(f"./out_msg.{file_encoding.value}"), debug_outfile
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
            file_encoding=FileEncoding(args.encoding),
            debug_dir=args.debug_directory,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
