"""Logic for waiting on task set."""

import asyncio
import logging
from typing import Dict, List, Set, Tuple

import mqclient as mq
from mqclient.broker_client_interface import Message

from ..utils.utils import all_task_errors_string

LOGGER = logging.getLogger(__name__)

AsyncioTaskMessages = Dict[asyncio.Task, Message]  # type: ignore[type-arg]


async def wait_on_tasks_with_ack(
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
        LOGGER.error(all_task_errors_string(previous_task_errors))

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
            LOGGER.exception(e)
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
