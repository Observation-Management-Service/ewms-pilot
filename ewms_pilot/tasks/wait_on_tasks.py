"""Logic for waiting on task set."""

import asyncio
import logging

import mqclient as mq
from mqclient.broker_client_interface import Message

from .io import NoTaskResponseException
from .map import TaskMapping
from ..utils.utils import dump_all_taskmaps, dump_tallies, dump_task_runtime_stats

LOGGER = logging.getLogger(__name__)


async def _nack(
    exception: BaseException,
    sub: mq.queue.ManualQueueSubResource,
    msg: Message,
) -> None:  # type: ignore[type-arg]
    LOGGER.exception(exception)
    LOGGER.error(
        f"TASK FAILED ({repr(exception)}) -- attempting to nack input-event message..."
    )
    try:
        await sub.nack(msg)
    except Exception as e:
        # LOGGER.exception(e)
        LOGGER.error(f"Could not nack: {repr(e)}")


async def wait_on_tasks_with_ack(
    sub: mq.queue.ManualQueueSubResource,
    pub: mq.queue.QueuePubResource,
    task_maps: list[TaskMapping],
    timeout: int,
) -> None:
    """Get finished tasks and ack/nack their messages."""
    if not any(tm for tm in task_maps if tm.is_pending):
        return

    # wait for next task
    LOGGER.debug("Waiting on tasks to finish...")
    newly_done, _ = await asyncio.wait(
        [tm.asyncio_task for tm in task_maps if tm.is_pending],
        return_when=asyncio.FIRST_COMPLETED,
        timeout=timeout,
    )

    # HANDLE FINISHED TASK(S)
    # fyi, most likely one task in here, but 2+ could finish at same time
    for asyncio_task in newly_done:
        tmap = TaskMapping.get(task_maps, asyncio_task=asyncio_task)
        tmap.mark_done()
        try:
            output_event = await asyncio_task
        # SUCCESSFUL TASK W/O OUTPUT -> is ok, but nothing to send...
        except NoTaskResponseException:
            LOGGER.info("TASK FINISHED -- no output-event to send (this is ok).")
        # FAILED TASK! -> nack input message
        except Exception as e:
            tmap.error = e  # already marked as done, see above
            await _nack(e, sub, tmap.message)
            continue
        # SUCCESSFUL TASK W/ OUTPUT -> send...
        else:
            try:
                LOGGER.info("TASK FINISHED -- attempting to send output-event...")
                await pub.send(output_event)
            except Exception as e:
                tmap.error = e  # already marked as done, see above
                # -> failed to send = FAILED TASK! -> nack input-event message
                LOGGER.error(
                    f"Failed to send finished task's output-event: {repr(e)}"
                    f" -- the task is now considered failed."
                )
                await _nack(e, sub, tmap.message)
                continue

        # now, ack input message
        try:
            LOGGER.info("Now, attempting to ack input-event message...")
            await sub.ack(tmap.message)
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

    # log
    if newly_done:
        # new tallies
        LOGGER.info("Update (just now):")
        dump_all_taskmaps([tm for tm in task_maps if tm.asyncio_task in newly_done])
        dump_tallies(
            [tm for tm in task_maps if tm.asyncio_task in newly_done],
            dump_n_pending=False,
        )

        # overall tallies
        LOGGER.info("Overall:")
        dump_tallies(task_maps)
        dump_task_runtime_stats(task_maps)
