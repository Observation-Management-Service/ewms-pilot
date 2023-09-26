"""API for launching an MQ-task pilot."""


import argparse
import asyncio
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import mqclient as mq
from mqclient.broker_client_interface import Message
from wipac_dev_tools import argparse_tools, logging_tools

from . import utils
from .config import ENV, LOGGER
from .io import FileType, UniversalFileInterface
from .task import process_msg_task

# fmt:off
if sys.version_info[1] < 10:
    # this is built in for py3.10+
    async def anext(ait):
        return await ait.__anext__()
# fmt:on


AsyncioTaskMessages = Dict[asyncio.Task, Message]  # type: ignore[type-arg]


# if there's an error, have the cluster try again (probably a system error)
_EXCEPT_ERRORS = False

_DEFAULT_TIMEOUT_INCOMING = 1  # second
_DEFAULT_TIMEOUT_OUTGOING = 1  # second

_REFRESH_INTERVAL = 1  # sec -- the time between transitioning phases of the main loop


def _all_task_errors_string(task_errors: List[BaseException]) -> str:
    return (
        f"{len(task_errors)} TASK(S) FAILED: "
        f"{', '.join(repr(e) for e in task_errors)}"
    )


@utils.async_htchirping
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
    timeout_incoming: int = _DEFAULT_TIMEOUT_INCOMING,
    timeout_outgoing: int = _DEFAULT_TIMEOUT_OUTGOING,
    #
    file_writer: Callable[[Any, Path], None] = UniversalFileInterface.write,
    file_reader: Callable[[Path], Any] = UniversalFileInterface.read,
    #
    debug_dir: Optional[Path] = None,
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
            #
            task_timeout,
            multitasking,
        )
        if task_errors:
            raise RuntimeError(_all_task_errors_string(task_errors))
    except Exception as e:
        if quarantine_time:
            msg = f"{e} (Quarantining for {quarantine_time} seconds)"
            utils.chirp_status(msg)
            LOGGER.error(msg)
            await asyncio.sleep(quarantine_time)
        raise


async def _wait_on_tasks_with_ack(
    sub: mq.queue.ManualQueueSubResource,
    pub: mq.queue.QueuePubResource,
    tasks_msgs: AsyncioTaskMessages,
    previous_task_errors: List[BaseException],
    timeout: int,
) -> Tuple[AsyncioTaskMessages, List[BaseException]]:
    """Get finished tasks and ack/nack their messages.

    Returns:
        Tuple:
            AsyncioTaskMessages: pending tasks and
            List[BaseException]: failed tasks' exceptions (plus those in `previous_task_errors`)
    """
    pending: Set[asyncio.Task] = set(tasks_msgs.keys())  # type: ignore[type-arg]
    if not pending:
        return {}, previous_task_errors

    async def handle_failed_task(task: asyncio.Task, exception: BaseException) -> None:  # type: ignore[type-arg]
        previous_task_errors.append(exception)
        LOGGER.error(
            f"TASK FAILED ({repr(exception)}) -- attempting to nack original message..."
        )
        try:
            await sub.nack(tasks_msgs[task])
        except Exception as e:
            # LOGGER.exception(e)
            LOGGER.error(f"Could not nack: {repr(e)}")
        LOGGER.error(_all_task_errors_string(previous_task_errors))

    # wait for next task
    LOGGER.debug("Waiting on tasks...")
    done, pending = await asyncio.wait(
        pending,
        return_when=asyncio.FIRST_COMPLETED,
        timeout=timeout,
    )

    # HANDLE FINISHED TASK(S)
    # fyi, most likely one task in here, but 2+ could finish at same time
    for task in done:
        try:
            result = await task
        except Exception as e:
            # FAILED TASK!
            await handle_failed_task(task, e)
            continue

        # SUCCESSFUL TASK -> send result
        try:
            LOGGER.info("TASK FINISHED -- attempting to send result message...")
            await pub.send(result)
        except Exception as e:
            # -> failed to send = FAILED TASK!
            LOGGER.error(
                f"Failed to send finished task's result: {repr(e)}"
                f" -- task now considered as failed"
            )
            await handle_failed_task(task, e)
            continue

        # SUCCESSFUL TASK -> result sent -> ack original message
        try:
            LOGGER.info("Now, attempting to ack original message...")
            await sub.ack(tasks_msgs[task])
        except mq.broker_client_interface.AckException as e:
            # -> result sent -> ack failed = that's okay!
            LOGGER.error(
                f"Could not ack ({repr(e)}) -- not counting as a failed task"
                " since task's result was sent successfully -- "
                "NOTE: outgoing queue may eventually get"
                " duplicate result when original message is"
                " re-delivered by broker to another pilot"
                " & the new result is sent"
            )

    if done:
        LOGGER.info(f"{len(tasks_msgs)-len(pending)} Tasks Finished")

    return (
        {t: msg for t, msg in tasks_msgs.items() if t in pending},
        # this now also includes tasks that finished this round
        previous_task_errors,
    )


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


class Housekeeping:
    """Manage and perform housekeeping."""

    RABBITMQ_HEARTBEAT_INTERVAL = 5

    def __init__(self) -> None:
        self.prev_rabbitmq_heartbeat = 0.0

    async def work(
        self,
        in_queue: mq.Queue,
        sub: mq.queue.ManualQueueSubResource,
        pub: mq.queue.QueuePubResource,
    ) -> None:
        """Do housekeeping."""
        await asyncio.sleep(0)  # hand over control to other async tasks

        # rabbitmq heartbeats
        # TODO: replace when https://github.com/Observation-Management-Service/MQClient/issues/56
        if in_queue._broker_client.NAME.lower() == "rabbitmq":
            if (
                time.time() - self.prev_rabbitmq_heartbeat
                > self.RABBITMQ_HEARTBEAT_INTERVAL
            ):
                self.prev_rabbitmq_heartbeat = time.time()
                for raw_q in [pub.pub, sub._sub]:
                    if raw_q.connection:  # type: ignore[attr-defined, union-attr]
                        LOGGER.info("sending heartbeat to RabbitMQ broker...")
                        raw_q.connection.process_data_events()  # type: ignore[attr-defined, union-attr]

        # TODO -- add other housekeeping


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
        and timeout_wait_for_first_message < _REFRESH_INTERVAL
    ):
        raise ValueError(
            f"'timeout_wait_for_first_message' cannot be less than {_REFRESH_INTERVAL}: "
            f"currently {timeout_wait_for_first_message}"
        )
    if timeout_incoming < _REFRESH_INTERVAL:
        raise ValueError(
            f"'timeout_incoming' cannot be less than {_REFRESH_INTERVAL}: "
            f"currently {timeout_incoming}"
        )
    in_queue.timeout = _REFRESH_INTERVAL
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
                        utils.chirp_status("Tasking")

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
            pending, task_errors = await _wait_on_tasks_with_ack(
                sub,
                pub,
                pending,
                previous_task_errors=task_errors,
                timeout=_REFRESH_INTERVAL,
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
            pending, task_errors = await _wait_on_tasks_with_ack(
                sub,
                pub,
                pending,
                previous_task_errors=task_errors,
                timeout=_REFRESH_INTERVAL,
            )

    # log/chirp
    chirp_msg = f"Done Tasking: completed {total_msg_count} task(s)"
    utils.chirp_status(chirp_msg)
    LOGGER.info(chirp_msg)
    # check if anything actually processed
    if not total_msg_count:
        LOGGER.warning("No Messages Were Received.")

    # cleanup
    if not list(staging_dir.iterdir()):  # if empty
        shutil.rmtree(staging_dir)  # rm -r

    return task_errors


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
        "--infile-type",
        type=FileType,
        help="the file type (extension) to use for files written for the pilot's subprocess",
    )
    parser.add_argument(
        "--outfile-type",
        type=FileType,
        help="the file type (exception) of the file to read from the pilot's subprocess",
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
        default=_DEFAULT_TIMEOUT_INCOMING,
        type=int,
        help="timeout (seconds) for messages TO pilot",
    )
    parser.add_argument(
        "--timeout-outgoing",
        default=_DEFAULT_TIMEOUT_OUTGOING,
        type=int,
        help="timeout (seconds) for messages FROM pilot",
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
            ftype_to_subproc=args.infile_type,
            ftype_from_subproc=args.outfile_type,
            #
            broker_address=args.broker,
            auth_token=args.auth_token,
            queue_incoming=args.queue_incoming,
            queue_outgoing=args.queue_outgoing,
            prefetch=args.prefetch,
            timeout_wait_for_first_message=args.timeout_wait_for_first_message,
            timeout_incoming=args.timeout_incoming,
            timeout_outgoing=args.timeout_outgoing,
            # file_writer=UniversalFileInterface.write,
            # file_reader=UniversalFileInterface.read,
            debug_dir=args.debug_directory,
            task_timeout=args.task_timeout,
            quarantine_time=args.quarantine_time,
            multitasking=args.multitasking,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
