"""The Client service."""


import pickle
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

import asyncstdlib as asl
import mqclient_pulsar as mq

from . import LOGGER

OUT_PKL = Path("out_msg.pkl")
IN_PKL = Path("in_msg.pkl")


def inmsg_to_infile(in_msg: Any, debug_infile: Optional[Path]) -> Path:
    """Write the msg to the `IN` file.

    Also, dump to a file for debugging (if not "").
    """
    with open(IN_PKL, "wb") as f:
        LOGGER.info(f"Pickle-dumping in-payload to file: {str(in_msg)} @ {IN_PKL}")
        pickle.dump(in_msg, f)
    LOGGER.info(f"Pickle File:: {IN_PKL} ({IN_PKL.stat().st_size} bytes)")

    if debug_infile:  # for debugging
        with open(debug_infile, "wb") as f:
            LOGGER.info(
                f"Pickle-dumping in-payload to file: {str(in_msg)} @ {debug_infile}"
            )
            pickle.dump(in_msg, f)
        LOGGER.info(
            f"Pickle File:: {debug_infile} ({debug_infile.stat().st_size} bytes)"
        )

    return IN_PKL


def outfile_to_outmsg(debug_outfile: Optional[Path]) -> Any:
    """Read the msg from the `OUT` file.

    Also, dump to a file for debugging (if not "").
    """
    with open(OUT_PKL, "rb") as f:
        out_msg = pickle.load(f)
        LOGGER.info(f"Pickle-loaded out-payload from file: {str(out_msg)} @ {OUT_PKL}")
    LOGGER.info(f"Pickle File:: {OUT_PKL} ({OUT_PKL.stat().st_size} bytes)")
    OUT_PKL.unlink()  # rm

    if debug_outfile:  # for debugging
        with open(debug_outfile, "wb") as f:
            LOGGER.info(
                f"Pickle-dumping out-payload to file: {str(out_msg)} @ {debug_outfile}"
            )
            pickle.dump(out_msg, f)
        LOGGER.info(
            f"Pickle File:: {debug_outfile} ({debug_outfile.stat().st_size} bytes)"
        )

    return out_msg


async def consume_and_reply(
    cmd: str,
    broker: str,  # for mq
    auth_token: str,  # for mq
    queue_to_clients: str,  # for mq
    queue_from_clients: str,  # for mq
    timeout_to_clients: int,  # for mq
    timeout_from_clients: int,  # for mq
    debug_directory: Optional[Path] = None,
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
            if debug_directory:
                debug_time = time.time()
                debug_infile = debug_directory / f"{debug_time}.in.pkl"
                debug_outfile = debug_directory / f"{debug_time}.out.pkl"

            # write
            inmsg_to_infile(in_msg, debug_infile)

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
            if not OUT_PKL.exists():
                LOGGER.error("Out file was not written for in-payload")
                raise RuntimeError("Out file was not written for in-payload")

            # get
            out_msg = outfile_to_outmsg(debug_outfile)

            # send
            LOGGER.info("Sending out-payload to server...")
            await pub.send(out_msg)

    # check if anything was actually processed
    try:
        n_msgs = i + 1  # 0-indexing :) # pylint: disable=undefined-loop-variable
    except NameError:
        raise RuntimeError("No Messages Were Received.")
    LOGGER.info(f"Done Processing: handled {n_msgs} messages")
