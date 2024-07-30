"""API for launching an MQ-task pilot."""

import asyncio
import sys
import uuid
from typing import List, Optional

import mqclient as mq

from . import htchirp_tools
from .config import (
    DirectoryCatalog,
    ENV,
    LOGGER,
    REFRESH_INTERVAL,
)
from .housekeeping import Housekeeping
from .tasks.io import FileExtension
from .tasks.task import process_msg_task
from .tasks.wait_on_tasks import AsyncioTaskMessages, wait_on_tasks_with_ack
from .utils.runner import run_container
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
    task_image: str = ENV.EWMS_PILOT_TASK_IMAGE,
    task_args: str = ENV.EWMS_PILOT_TASK_ARGS,
    task_timeout: Optional[int] = ENV.EWMS_PILOT_TASK_TIMEOUT,
    max_concurrent_tasks: int = ENV.EWMS_PILOT_MAX_CONCURRENT_TASKS,
    #
    # incoming queue
    queue_incoming: str = ENV.EWMS_PILOT_QUEUE_INCOMING,
    queue_incoming_auth_token: str = ENV.EWMS_PILOT_QUEUE_INCOMING_AUTH_TOKEN,
    queue_incoming_broker_type: str = ENV.EWMS_PILOT_QUEUE_INCOMING_BROKER_TYPE,
    queue_incoming_broker_address: str = ENV.EWMS_PILOT_QUEUE_INCOMING_BROKER_ADDRESS,
    # incoming queue - settings
    prefetch: int = ENV.EWMS_PILOT_PREFETCH,
    timeout_wait_for_first_message: Optional[
        int
    ] = ENV.EWMS_PILOT_TIMEOUT_QUEUE_WAIT_FOR_FIRST_MESSAGE,
    timeout_incoming: int = ENV.EWMS_PILOT_TIMEOUT_QUEUE_INCOMING,
    #
    # outgoing queue
    queue_outgoing: str = ENV.EWMS_PILOT_QUEUE_OUTGOING,
    queue_outgoing_auth_token: str = ENV.EWMS_PILOT_QUEUE_OUTGOING_AUTH_TOKEN,
    queue_outgoing_broker_type: str = ENV.EWMS_PILOT_QUEUE_OUTGOING_BROKER_TYPE,
    queue_outgoing_broker_address: str = ENV.EWMS_PILOT_QUEUE_OUTGOING_BROKER_ADDRESS,
    #
    # for subprocess
    infile_type: str = ENV.EWMS_PILOT_INFILE_TYPE,
    outfile_type: str = ENV.EWMS_PILOT_OUTFILE_TYPE,
    #
    # init
    init_image: str = ENV.EWMS_PILOT_INIT_IMAGE,
    init_args: str = ENV.EWMS_PILOT_INIT_ARGS,
    init_timeout: Optional[int] = ENV.EWMS_PILOT_INIT_TIMEOUT,
    #
    # misc settings
    quarantine_time: int = ENV.EWMS_PILOT_QUARANTINE_TIME,
) -> None:
    """Communicate with server and outsource processing to subprocesses."""
    LOGGER.info("Making MQClient queue connections...")
    chirper = htchirp_tools.Chirper()
    chirper.initial_chirp()

    if not queue_incoming or not queue_outgoing:
        raise RuntimeError("Must define an incoming and an outgoing queue")

    housekeeper = Housekeeping(chirper)

    try:
        # Init command
        if init_image:
            await run_init_container(
                init_image,
                init_args,
                init_timeout,
                housekeeper,
            )

        # connect queues
        in_queue = mq.Queue(
            queue_incoming_broker_type,
            address=queue_incoming_broker_address,
            name=queue_incoming,
            prefetch=prefetch,
            auth_token=queue_incoming_auth_token,
            except_errors=_EXCEPT_ERRORS,
            # timeout=timeout_incoming, # manually set below
        )
        out_queue = mq.Queue(
            queue_outgoing_broker_type,
            address=queue_outgoing_broker_address,
            name=queue_outgoing,
            auth_token=queue_outgoing_auth_token,
            except_errors=_EXCEPT_ERRORS,
            # timeout=timeout_outgoing,  # no timeout needed b/c this queue is only for pub
        )

        # MQ tasks
        await _consume_and_reply(
            task_image,
            task_args,
            in_queue,
            out_queue,
            FileExtension(infile_type),
            FileExtension(outfile_type),
            #
            timeout_wait_for_first_message,
            timeout_incoming,
            #
            task_timeout,
            max_concurrent_tasks,
            #
            housekeeper,
        )

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
async def run_init_container(
    init_image: str,
    init_args: str,
    init_timeout: Optional[int],
    housekeeper: Housekeeping,
) -> None:
    """Run the init container with the given arguments."""
    await housekeeper.running_init_container()

    dirs = DirectoryCatalog(f"init-{uuid.uuid4().hex}")
    dirs.outputs_on_host.mkdir(parents=True, exist_ok=False)

    task = asyncio.create_task(
        run_container(
            init_image,
            init_args,
            init_timeout,
            dirs.outputs_on_host / "stdoutfile",
            dirs.outputs_on_host / "stderrfile",
            dirs.assemble_bind_mounts(external_directories=True),
            f"--env EWMS_TASK_PILOT_STORE_DIR={dirs.pilot_store.in_container}",
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
    if not ENV.EWMS_PILOT_KEEP_ALL_TASK_FILES:
        dirs.rm_unique_dirs()

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
    task_image: str,
    task_args: str,
    #
    in_queue: mq.Queue,
    out_queue: mq.Queue,
    #
    # for subprocess
    infile_ext: FileExtension,
    outfile_ext: FileExtension,
    #
    timeout_wait_for_first_message: Optional[int],
    timeout_incoming: int,
    #
    task_timeout: Optional[int],
    max_concurrent_tasks: int,
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
        LOGGER.info(f"Processing up to {max_concurrent_tasks} tasks concurrently")
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
            if len(pending) >= max_concurrent_tasks:
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
                            task_image,
                            task_args,
                            task_timeout,
                            infile_ext,
                            outfile_ext,
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
