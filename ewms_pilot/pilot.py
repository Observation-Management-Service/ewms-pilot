"""API for launching an MQ-task pilot."""


import asyncio
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, List, Optional, Union

import mqclient as mq

from . import htchirp_tools
from .config import (
    DEFAULT_TIMEOUT_INCOMING,
    DEFAULT_TIMEOUT_OUTGOING,
    ENV,
    LOGGER,
    REFRESH_INTERVAL,
)
from .housekeeping import Housekeeping
from .tasks.io import FileType, UniversalFileInterface
from .tasks.task import process_msg_task
from .tasks.wait_on_tasks import AsyncioTaskMessages, wait_on_tasks_with_ack
from .utils.utils import all_task_errors_string

# fmt:off
if sys.version_info[1] < 10:
    # this is built in for py3.10+
    async def anext(ait):
        return await ait.__anext__()
# fmt:on


# if there's an error, have the cluster try again (probably a system error)
_EXCEPT_ERRORS = False


@htchirp_tools.async_htchirping
async def consume_and_reply(
    cmd: str,
    #
    queue_incoming: str,
    queue_outgoing: str,
    #
    # for subprocess
    ftype_to_subproc: Union[str, FileType],
    ftype_from_subproc: Union[str, FileType],
    #
    # for mq
    broker_client: str = ENV.EWMS_PILOT_BROKER_CLIENT,
    broker_address: str = ENV.EWMS_PILOT_BROKER_ADDRESS,
    auth_token: str = ENV.EWMS_PILOT_BROKER_AUTH_TOKEN,
    #
    prefetch: int = ENV.EWMS_PILOT_PREFETCH,
    #
    timeout_wait_for_first_message: Optional[int] = None,
    timeout_incoming: int = DEFAULT_TIMEOUT_INCOMING,
    timeout_outgoing: int = DEFAULT_TIMEOUT_OUTGOING,
    #
    file_writer: Callable[[Any, Path], None] = UniversalFileInterface.write,
    file_reader: Callable[[Path], Any] = UniversalFileInterface.read,
    #
    debug_dir: Optional[Path] = None,
    dump_task_output: bool = ENV.EWMS_PILOT_DUMP_TASK_OUTPUT,
    #
    task_timeout: Optional[int] = ENV.EWMS_PILOT_TASK_TIMEOUT,
    quarantine_time: int = ENV.EWMS_PILOT_QUARANTINE_TIME,
    #
    multitasking: int = ENV.EWMS_PILOT_CONCURRENT_TASKS,
) -> None:
    """Communicate with server and outsource processing to subprocesses.

    Arguments:
        `timeout_wait_for_first_message`: if None, use 'timeout_incoming'
    """
    LOGGER.info("Making MQClient queue connections...")

    if not queue_incoming or not queue_outgoing:
        raise RuntimeError("Must define an incoming and an outgoing queue")

    if not isinstance(ftype_to_subproc, FileType):
        ftype_to_subproc = FileType(ftype_to_subproc)
    if not isinstance(ftype_from_subproc, FileType):
        ftype_from_subproc = FileType(ftype_from_subproc)

    in_queue = mq.Queue(
        broker_client,
        address=broker_address,
        name=queue_incoming,
        prefetch=prefetch,
        auth_token=auth_token,
        except_errors=_EXCEPT_ERRORS,
        # timeout=timeout_incoming, # manually set below
    )
    out_queue = mq.Queue(
        broker_client,
        address=broker_address,
        name=queue_outgoing,
        auth_token=auth_token,
        except_errors=_EXCEPT_ERRORS,
        timeout=timeout_outgoing,
    )

    try:
        task_errors = await _consume_and_reply(
            cmd,
            in_queue,
            out_queue,
            ftype_to_subproc,
            ftype_from_subproc,
            #
            timeout_wait_for_first_message,
            timeout_incoming,
            file_writer,
            file_reader,
            #
            debug_dir if debug_dir else Path("./tmp"),
            bool(debug_dir),
            dump_task_output,
            #
            task_timeout,
            multitasking,
        )
        if task_errors:
            raise RuntimeError(all_task_errors_string(task_errors))
    except Exception as e:
        if quarantine_time:
            msg = f"{e} (Quarantining for {quarantine_time} seconds)"
            htchirp_tools.chirp_status(msg)
            LOGGER.error(msg)
            await asyncio.sleep(quarantine_time)
        raise


def listener_loop_exit(
    task_errors: List[BaseException],
    current_msg_waittime: float,
    msg_waittime_timeout: float,
) -> bool:
    """Essentially a big IF condition -- but now with logging!"""
    if task_errors:
        LOGGER.info("1+ Tasks Failed: waiting for remaining tasks")
        return True
    if current_msg_waittime > msg_waittime_timeout:
        LOGGER.info(f"Timed out waiting for incoming message: {msg_waittime_timeout=}")
        return True
    return False


async def _consume_and_reply(
    cmd: str,
    #
    in_queue: mq.Queue,
    out_queue: mq.Queue,
    #
    # for subprocess
    ftype_to_subproc: FileType,
    ftype_from_subproc: FileType,
    #
    timeout_wait_for_first_message: Optional[int],
    timeout_incoming: int,
    #
    file_writer: Callable[[Any, Path], None],
    file_reader: Callable[[Path], Any],
    #
    staging_dir: Path,
    keep_debug_dir: bool,
    dump_task_output: bool,
    #
    task_timeout: Optional[int],
    multitasking: int,
) -> List[BaseException]:
    """Consume and reply loop.

    Return errors of failed tasks.
    """
    pending: AsyncioTaskMessages = {}
    task_errors: List[BaseException] = []

    housekeeper = Housekeeping()

    # timeouts
    if (
        timeout_wait_for_first_message is not None
        and timeout_wait_for_first_message < REFRESH_INTERVAL
    ):
        raise ValueError(
            f"'timeout_wait_for_first_message' cannot be less than {REFRESH_INTERVAL}: "
            f"currently {timeout_wait_for_first_message}"
        )
    if timeout_incoming < REFRESH_INTERVAL:
        raise ValueError(
            f"'timeout_incoming' cannot be less than {REFRESH_INTERVAL}: "
            f"currently {timeout_incoming}"
        )
    in_queue.timeout = REFRESH_INTERVAL
    msg_waittime_timeout = timeout_wait_for_first_message or timeout_incoming

    # GO!
    total_msg_count = 0
    LOGGER.info(
        "Listening for messages from server to process tasks then send results..."
    )
    #
    # open pub & sub
    async with out_queue.open_pub() as pub, in_queue.open_sub_manual_acking() as sub:
        LOGGER.info(f"Processing up to {multitasking} tasks concurrently")
        message_iterator = sub.iter_messages()
        #
        # "listener loop" -- get messages and do tasks
        # intermittently halting to process housekeeping things
        #
        msg_waittime_current = 0.0
        while not listener_loop_exit(
            task_errors, msg_waittime_current, msg_waittime_timeout
        ):
            await housekeeper.work(in_queue, sub, pub)
            #
            # get messages/tasks
            if len(pending) >= multitasking:
                LOGGER.debug("At max task concurrency limit")
            else:
                LOGGER.debug("Listening for incoming message...")
                try:
                    in_msg = await anext(message_iterator)  # -> in_queue.timeout
                    msg_waittime_current = 0.0
                    total_msg_count += 1
                    LOGGER.info(f"Got a task to process (#{total_msg_count}): {in_msg}")

                    # after the first message, set the timeout to the "normal" amount
                    msg_waittime_timeout = timeout_incoming

                    if total_msg_count == 1:
                        htchirp_tools.chirp_status("Tasking")

                    task = asyncio.create_task(
                        process_msg_task(
                            in_msg,
                            cmd,
                            task_timeout,
                            ftype_to_subproc,
                            ftype_from_subproc,
                            file_writer,
                            file_reader,
                            staging_dir,
                            keep_debug_dir,
                            dump_task_output,
                        )
                    )
                    pending[task] = in_msg
                    continue  # we got one message, so maybe the queue is saturated
                except StopAsyncIteration:
                    # no message this round
                    #   incrementing by the timeout value allows us to
                    #   not worry about time not spent waiting for a message
                    msg_waittime_current += in_queue.timeout
                    message_iterator = sub.iter_messages()

            # wait on finished task (or timeout)
            pending, task_errors = await wait_on_tasks_with_ack(
                sub,
                pub,
                pending,
                previous_task_errors=task_errors,
                timeout=REFRESH_INTERVAL,
            )

        LOGGER.info("Done listening for messages")

        #
        # "clean up loop" -- wait for remaining tasks
        # intermittently halting to process housekeeping things
        #
        if pending:
            LOGGER.debug("Waiting for remaining tasks to finish...")
        while pending:
            await housekeeper.work(in_queue, sub, pub)
            # wait on finished task (or timeout)
            pending, task_errors = await wait_on_tasks_with_ack(
                sub,
                pub,
                pending,
                previous_task_errors=task_errors,
                timeout=REFRESH_INTERVAL,
            )

    # log/chirp
    chirp_msg = f"Done Tasking: completed {total_msg_count} task(s)"
    htchirp_tools.chirp_status(chirp_msg)
    LOGGER.info(chirp_msg)
    # check if anything actually processed
    if not total_msg_count:
        LOGGER.warning("No Messages Were Received.")

    # cleanup
    if not list(staging_dir.iterdir()):  # if empty
        shutil.rmtree(staging_dir)  # rm -r

    return task_errors
