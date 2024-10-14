"""API for launching an MQ-task pilot."""

import asyncio
import logging
import sys
import time

import mqclient as mq

from . import htchirp_tools
from .config import (
    ENV,
    REFRESH_INTERVAL,
)
from .housekeeping import Housekeeping
from .init_container.init_container import run_init_container
from .tasks.io import FileExtension
from .tasks.map import TaskMapping
from .tasks.task import process_msg_task
from .tasks.wait_on_tasks import wait_on_tasks_with_ack
from .utils.runner import ContainerRunner
from .utils.utils import (
    all_task_errors_string,
    dump_all_taskmaps,
    dump_tallies,
    dump_task_runtime_stats,
)

LOGGER = logging.getLogger(__name__)

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
    task_timeout: int | None = ENV.EWMS_PILOT_TASK_TIMEOUT,
    max_concurrent_tasks: int = ENV.EWMS_PILOT_MAX_CONCURRENT_TASKS,
    #
    # incoming queue
    queue_incoming: str = ENV.EWMS_PILOT_QUEUE_INCOMING,
    queue_incoming_auth_token: str = ENV.EWMS_PILOT_QUEUE_INCOMING_AUTH_TOKEN,
    queue_incoming_broker_type: str = ENV.EWMS_PILOT_QUEUE_INCOMING_BROKER_TYPE,
    queue_incoming_broker_address: str = ENV.EWMS_PILOT_QUEUE_INCOMING_BROKER_ADDRESS,
    # incoming queue - settings
    prefetch: int = ENV.EWMS_PILOT_PREFETCH,
    timeout_wait_for_first_message: (
        int | None
    ) = ENV.EWMS_PILOT_TIMEOUT_QUEUE_WAIT_FOR_FIRST_MESSAGE,
    timeout_incoming: int = ENV.EWMS_PILOT_TIMEOUT_QUEUE_INCOMING,
    #
    # outgoing queue
    queue_outgoing: str = ENV.EWMS_PILOT_QUEUE_OUTGOING,
    queue_outgoing_auth_token: str = ENV.EWMS_PILOT_QUEUE_OUTGOING_AUTH_TOKEN,
    queue_outgoing_broker_type: str = ENV.EWMS_PILOT_QUEUE_OUTGOING_BROKER_TYPE,
    queue_outgoing_broker_address: str = ENV.EWMS_PILOT_QUEUE_OUTGOING_BROKER_ADDRESS,
    #
    # for subprocess
    infile_ext: str = ENV.EWMS_PILOT_INFILE_EXT,
    outfile_ext: str = ENV.EWMS_PILOT_OUTFILE_EXT,
    #
    # init
    init_image: str = ENV.EWMS_PILOT_INIT_IMAGE,
    init_args: str = ENV.EWMS_PILOT_INIT_ARGS,
    init_timeout: int | None = ENV.EWMS_PILOT_INIT_TIMEOUT,
    #
    # misc settings
    quarantine_time: int = ENV.EWMS_PILOT_QUARANTINE_TIME,
) -> None:
    """Communicate with server and outsource processing to subprocesses."""
    LOGGER.info("Making MQClient queue connections...")
    chirper = htchirp_tools.Chirper()
    chirper.initial_chirp()

    if not queue_incoming or not queue_outgoing:
        raise RuntimeError("Incoming and/or outgoing queues were not provided.")

    if not task_image:
        raise RuntimeError("Task image was not provided.")

    housekeeper = Housekeeping(chirper)

    try:
        # Init command
        if init_image:
            await run_init_container(
                ContainerRunner(
                    init_image,
                    init_args,
                    init_timeout,
                    ENV.EWMS_PILOT_INIT_ENV_JSON,
                ),
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

        task_runner = ContainerRunner(
            task_image,
            task_args,
            task_timeout,
            ENV.EWMS_PILOT_TASK_ENV_JSON,
        )

        # MQ tasks
        await _consume_and_reply(
            task_runner,
            #
            in_queue,
            out_queue,
            FileExtension(infile_ext),
            FileExtension(outfile_ext),
            #
            timeout_wait_for_first_message,
            timeout_incoming,
            #
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


def listener_loop_exit(
    task_errors: list[BaseException],
    current_msg_waittime: float,
    msg_waittime_timeout: float,
) -> bool:
    """Essentially a big IF condition -- but now with logging!"""
    # ERRORS?
    if task_errors and ENV.EWMS_PILOT_STOP_LISTENING_ON_TASK_ERROR:
        if any(type(e).__name__ not in ENV.EWMS_PILOT_OKAY_ERRORS for e in task_errors):
            # ^^^ equivalent to "if not all(name in ENV.EWMS_PILOT_OKAY_ERRORS ...):", but faster
            LOGGER.info("1+ Tasks Failed: no longer receiving incoming messages")
            return True
        else:
            LOGGER.info(
                "1+ Tasks Failed: but all failed with \"okay\" errors ('EWMS_PILOT_OKAY_ERRORS'), "
                "continuing to receive incoming messages"
            )
    # TIMEOUT?
    if current_msg_waittime > msg_waittime_timeout:
        LOGGER.info(f"Timed out waiting for incoming message: {msg_waittime_timeout=}")
        return True
    # ALL GOOD, LET'S GET MORE MESSAGES!
    return False


@htchirp_tools.async_htchirp_error_wrapper
async def _consume_and_reply(
    task_runner: ContainerRunner,
    #
    in_queue: mq.Queue,
    out_queue: mq.Queue,
    #
    # for subprocess
    infile_ext: FileExtension,
    outfile_ext: FileExtension,
    #
    timeout_wait_for_first_message: int | None,
    timeout_incoming: int,
    #
    max_concurrent_tasks: int,
    #
    housekeeper: Housekeeping,
) -> None:
    """Consume and reply loop.

    Raise an aggregated `RuntimeError` for errors of failed tasks.
    """
    await housekeeper.basic_housekeeping()

    task_maps: list[TaskMapping] = []

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
            [tm.error for tm in task_maps if tm.error],
            msg_waittime_current,
            msg_waittime_timeout,
        ):
            await housekeeper.queue_housekeeping(in_queue, sub, pub)
            #
            # get messages/tasks
            if TaskMapping.n_pending(task_maps) >= max_concurrent_tasks:
                LOGGER.debug("At max task concurrency limit")
            else:
                LOGGER.debug("Listening for incoming message...")
                #
                # TRY TO GET A MESSAGE
                try:  # StopAsyncIteration -> in_queue.timeout
                    in_msg = await anext(message_iterator)
                    msg_waittime_current = 0.0
                    LOGGER.info(
                        f"Got a task to process (#{len(task_maps)+1}): {in_msg}"
                    )

                    # after the first message, set the timeout to the "normal" amount
                    msg_waittime_timeout = timeout_incoming

                    # start task
                    task = asyncio.create_task(
                        process_msg_task(
                            in_msg,
                            task_runner,
                            infile_ext,
                            outfile_ext,
                        )
                    )
                    task_maps.append(
                        TaskMapping(
                            message=in_msg,
                            asyncio_task=task,
                            start_time=time.time(),
                        )
                    )
                    await housekeeper.message_received(len(task_maps))

                    continue  # we got one message, let's see if there's another
                #
                # NO MESSAGE THIS ROUND
                except StopAsyncIteration:
                    #   incrementing by the timeout value allows us to
                    #   not worry about time not spent waiting for a message
                    msg_waittime_current += in_queue.timeout
                    message_iterator = sub.iter_messages()

            # WE GOT AS MANY CONCURRENT MESSAGES AS POSSIBLE (max concurrency or no message in in-queue)
            # wait on finished task (or timeout)
            await wait_on_tasks_with_ack(
                sub,
                pub,
                task_maps,
                timeout=REFRESH_INTERVAL,
            )
            await housekeeper.new_messages_done(
                TaskMapping.n_successful(task_maps),
                TaskMapping.n_failed(task_maps),
            )

        LOGGER.info("Done listening for messages")
        await housekeeper.exited_listener_loop()

        #
        # "clean up loop" -- wait for remaining tasks
        # intermittently halting to process housekeeping things
        #
        if any(tm for tm in task_maps if tm.is_pending):
            LOGGER.debug("Waiting for remaining tasks to finish...")
            await housekeeper.pending_remaining_tasks()
        while any(tm for tm in task_maps if tm.is_pending):
            await housekeeper.queue_housekeeping(in_queue, sub, pub)
            # wait on finished task (or timeout)
            await wait_on_tasks_with_ack(
                sub,
                pub,
                task_maps,
                timeout=REFRESH_INTERVAL,
            )
            await housekeeper.new_messages_done(
                TaskMapping.n_successful(task_maps),
                TaskMapping.n_failed(task_maps),
            )

    # log/chirp
    await housekeeper.done_tasking()
    LOGGER.info(f"Done Tasking: completed {len(task_maps)} task(s)")
    # check if anything actually processed
    if not task_maps:
        LOGGER.warning("No Messages Were Received.")

    # done
    if any(tm.error for tm in task_maps if tm.error):
        raise RuntimeError(
            all_task_errors_string([tm.error for tm in task_maps if tm.error])
        )

    # dumps about tasks
    dump_all_taskmaps(task_maps)
    dump_tallies(task_maps)
    dump_task_runtime_stats(task_maps)
