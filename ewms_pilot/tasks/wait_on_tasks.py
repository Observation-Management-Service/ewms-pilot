"""Logic for waiting on task set."""

import asyncio
import logging

import mqclient as mq
from mqclient.broker_client_interface import Message

from .io import NoTaskResponseException
from ..utils.utils import all_task_errors_string

LOGGER = logging.getLogger(__name__)

AsyncioTaskMessages = dict[asyncio.Task, Message]  # type: ignore[type-arg]


async def _nack_and_record_error(
    prev_task_errors: list[BaseException],
    exception: BaseException,
    sub: mq.queue.ManualQueueSubResource,
    msg: Message,
) -> None:  # type: ignore[type-arg]
    LOGGER.exception(exception)
    prev_task_errors.append(exception)
    LOGGER.error(
        f"TASK FAILED ({repr(exception)}) -- attempting to nack input-event message..."
    )
    try:
        await sub.nack(msg)
    except Exception as e:
        # LOGGER.exception(e)
        LOGGER.error(f"Could not nack: {repr(e)}")
    LOGGER.error(all_task_errors_string(prev_task_errors))


async def wait_on_tasks_with_ack(
    sub: mq.queue.ManualQueueSubResource,
    pub: mq.queue.QueuePubResource,
    tasks_msgs: AsyncioTaskMessages,
    prev_task_errors: list[BaseException],
    timeout: int,
) -> tuple[AsyncioTaskMessages, list[BaseException]]:
    """Get finished tasks and ack/nack their messages.

    Returns:
        Tuple:
            AsyncioTaskMessages: pending tasks and
            list[BaseException]: failed tasks' exceptions (plus those in `previous_task_errors`)
    """
    pending: set[asyncio.Task] = set(tasks_msgs.keys())  # type: ignore[type-arg]
    if not pending:
        return {}, prev_task_errors

    # wait for next task
    LOGGER.debug("Waiting on tasks to finish...")
    done, pending = await asyncio.wait(
        pending,
        return_when=asyncio.FIRST_COMPLETED,
        timeout=timeout,
    )

    # HANDLE FINISHED TASK(S)
    # fyi, most likely one task in here, but 2+ could finish at same time
    for task in done:
        try:
            output_event = await task
        # SUCCESSFUL TASK W/O OUTPUT -> is ok, but nothing to send...
        except NoTaskResponseException:
            LOGGER.info("TASK FINISHED -- no output-event to send (this is ok).")
        # FAILED TASK! -> nack input message
        except Exception as e:
            await _nack_and_record_error(prev_task_errors, e, sub, tasks_msgs[task])
            continue
        # SUCCESSFUL TASK W/ OUTPUT -> send...
        else:
            try:
                LOGGER.info("TASK FINISHED -- attempting to send output-event...")
                await pub.send(output_event)
            except Exception as e:
                # -> failed to send = FAILED TASK! -> nack input-event message
                LOGGER.error(
                    f"Failed to send finished task's output-event: {repr(e)}"
                    f" -- the task is now considered failed."
                )
                await _nack_and_record_error(prev_task_errors, e, sub, tasks_msgs[task])
                continue

        # now, ack input message
        try:
            LOGGER.info("Now, attempting to ack input-event message...")
            await sub.ack(tasks_msgs[task])
        except mq.broker_client_interface.AckException as e:
            # -> task finished -> ack failed = that's okay!
            LOGGER.error(
                f"Could not ack ({repr(e)}) -- not counted as a failed task"
                " since task's output-event was sent successfully "
                "(if there was an output, check logs to guarantee that). "
                "NOTE: outgoing queue may eventually get"
                " duplicate output-event when original message is"
                " re-delivered by broker to another pilot"
                " & the new output-event is sent."
            )

    if done:
        LOGGER.info(f"{len(tasks_msgs)-len(pending)} Tasks Finished")

    return (
        {t: msg for t, msg in tasks_msgs.items() if t in pending},
        # this now also includes tasks that finished this round
        prev_task_errors,
    )
