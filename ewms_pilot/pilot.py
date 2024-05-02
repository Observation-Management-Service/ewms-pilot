"""API for launching an MQ-task pilot."""


import asyncio
import shutil
import sys
import uuid
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
from .utils.subproc import run_subproc
from .utils.utils import all_task_errors_string

# fmt:off
if sys.version_info[1] < 10:
    # this is built in for py3.10+
    async def anext(ait):
        return await ait.__anext__()
# fmt:on


# if there's an error, have the cluster try again (probably a system error)
_EXCEPT_ERRORS = False


@htchirp_tools.async_htchirp_error_wrapper
async def consume_and_reply(
    cmd: str,
    #
    queue_incoming: str = ENV.EWMS_PILOT_QUEUE_INCOMING,
    queue_outgoing: str = ENV.EWMS_PILOT_QUEUE_OUTGOING,
    #
    # for subprocess
    ftype_to_subproc: Union[str, FileType] = FileType.TXT,
    ftype_from_subproc: Union[str, FileType] = FileType.TXT,
    #
    init_cmd: str = "",
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
    init_timeout: Optional[int] = ENV.EWMS_PILOT_INIT_TIMEOUT,
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
    chirper = htchirp_tools.Chirper()
    chirper.initial_chirp()

    if not queue_incoming or not queue_outgoing:
        raise RuntimeError("Must define an incoming and an outgoing queue")

    if not isinstance(ftype_to_subproc, FileType):
        ftype_to_subproc = FileType(ftype_to_subproc)
    if not isinstance(ftype_from_subproc, FileType):
        ftype_from_subproc = FileType(ftype_from_subproc)

    housekeeper = Housekeeping(chirper)
    staging_dir = debug_dir if debug_dir else Path("./tmp")

    try:
        # Init command
        if init_cmd:
            await run_init_command(
                init_cmd,
                init_timeout,
                housekeeper,
                staging_dir,
                bool(debug_dir),
            )

        # connect queues
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

        # MQ tasks
        await _consume_and_reply(
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
            staging_dir,
            bool(debug_dir),
            dump_task_output,
            #
            task_timeout,
            multitasking,
            #
            housekeeper,
        )

        # cleanup
        if not list(staging_dir.iterdir()):  # if empty
            shutil.rmtree(staging_dir)  # rm -r

    # ERROR -> Quarantine
    except Exception as e:
        LOGGER.exception(e)
        chirper.chirp_status(htchirp_tools.PilotStatus.FatalError)
        if quarantine_time:
            LOGGER.warning(f"Quarantining for {quarantine_time} seconds")
            # do chirps ASAP during quarantine
            time_left = await chirper.chirp_backlog_until_done(quarantine_time, 5)
            await asyncio.sleep(time_left)
        raise
    else:
        chirper.chirp_status(htchirp_tools.PilotStatus.Done)
    finally:
        await chirper.chirp_backlog_until_done(10, 2)  # always clear the backlog
        chirper.close()


@htchirp_tools.async_htchirp_error_wrapper
async def run_init_command(
    init_cmd: str,
    init_timeout: Optional[int],
    housekeeper: Housekeeping,
    staging_dir: Path,
    keep_debug_dir: bool,
) -> None:
    """Run the init command."""
    await housekeeper.running_init_command()

    staging_subdir = staging_dir / f"init-{uuid.uuid4().hex}"
    staging_subdir.mkdir(parents=True, exist_ok=False)

    task = asyncio.create_task(
        run_subproc(
            init_cmd,
            init_timeout,
            staging_subdir / "stdoutfile",
            staging_subdir / "stderrfile",
            dump_output=True,
        )
    )
    pending = set([task])

    # wait with housekeeping
    while pending:
        _, pending = await asyncio.wait(
            pending,
            return_when=asyncio.ALL_COMPLETED,
            timeout=REFRESH_INTERVAL,
        )
        await housekeeper.basic_housekeeping()

    # see if the task failed
    try:
        await task
    except Exception as e:
        LOGGER.exception(e)
        raise

    # cleanup -- on success only
    if not keep_debug_dir:
        shutil.rmtree(staging_subdir)  # rm -r

    await housekeeper.finished_init_command()


def listener_loop_exit(
    task_errors: List[BaseException],
    current_msg_waittime: float,
    msg_waittime_timeout: float,
) -> bool:
    """Essentially a big IF condition -- but now with logging!"""
    if task_errors and ENV.EWMS_PILOT_STOP_LISTENING_ON_TASK_ERROR:
        LOGGER.info("1+ Tasks Failed: waiting for remaining tasks")
        return True
    if current_msg_waittime > msg_waittime_timeout:
        LOGGER.info(f"Timed out waiting for incoming message: {msg_waittime_timeout=}")
        return True
    return False


@htchirp_tools.async_htchirp_error_wrapper
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
    #
    housekeeper: Housekeeping,
) -> None:
    """Consume and reply loop.

    Raise an aggregated `RuntimeError` for errors of failed tasks.
    """
    await housekeeper.basic_housekeeping()

    pending: AsyncioTaskMessages = {}
    task_errors: List[BaseException] = []

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
        await housekeeper.entered_listener_loop()
        #
        # "listener loop" -- get messages and do tasks
        # intermittently halting to process housekeeping things
        #
        msg_waittime_current = 0.0
        while not listener_loop_exit(
            task_errors, msg_waittime_current, msg_waittime_timeout
        ):
            await housekeeper.queue_housekeeping(in_queue, sub, pub)
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

                    await housekeeper.message_recieved(total_msg_count)

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
            await housekeeper.new_messages_done(
                total_msg_count - len(pending) - len(task_errors),
                len(task_errors),
            )

        LOGGER.info("Done listening for messages")
        await housekeeper.exited_listener_loop()

        #
        # "clean up loop" -- wait for remaining tasks
        # intermittently halting to process housekeeping things
        #
        if pending:
            LOGGER.debug("Waiting for remaining tasks to finish...")
            await housekeeper.pending_remaining_tasks()
        while pending:
            await housekeeper.queue_housekeeping(in_queue, sub, pub)
            # wait on finished task (or timeout)
            pending, task_errors = await wait_on_tasks_with_ack(
                sub,
                pub,
                pending,
                previous_task_errors=task_errors,
                timeout=REFRESH_INTERVAL,
            )
            await housekeeper.new_messages_done(
                total_msg_count - len(pending) - len(task_errors),
                len(task_errors),
            )

    # log/chirp
    await housekeeper.done_tasking()
    LOGGER.info(f"Done Tasking: completed {total_msg_count} task(s)")
    # check if anything actually processed
    if not total_msg_count:
        LOGGER.warning("No Messages Were Received.")

    # done
    if task_errors:
        raise RuntimeError(all_task_errors_string(task_errors))
