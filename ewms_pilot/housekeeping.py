"""Housekeeping logic."""


import asyncio
import time
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

import mqclient as mq
from typing_extensions import ParamSpec

from . import htchirp_tools
from .config import LOGGER

T = TypeVar("T")
P = ParamSpec("P")


def with_basic_housekeeping(
    func: Callable[P, Coroutine[Any, Any, T]]
) -> Callable[P, Coroutine[Any, Any, T]]:
    """Send Condor Chirps at start, end, and if needed, final error."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        await args[0].basic_housekeeping()  # type: ignore[attr-defined]
        ret = await func(*args, **kwargs)
        return ret

    return wrapper


class Housekeeping:
    """Manage and perform housekeeping."""

    RABBITMQ_HEARTBEAT_INTERVAL = 5

    def __init__(self) -> None:
        self.prev_rabbitmq_heartbeat = 0.0
        htchirp_tools.chirp_new_total(0)
        htchirp_tools.chirp_new_failed_total(0)
        htchirp_tools.chirp_new_success_total(0)

    async def basic_housekeeping(
        self,
    ) -> None:
        """Do basic housekeeping."""
        # hand over control to other async tasks -- needed if using pkg as an import
        await asyncio.sleep(0)

    @with_basic_housekeeping
    async def running_init_command(self) -> None:
        """Update status for chirp."""
        htchirp_tools.chirp_status("Running init command")

    @with_basic_housekeeping
    async def finished_init_command(self) -> None:
        """Update status for chirp."""
        htchirp_tools.chirp_status("Finished init command")

    @with_basic_housekeeping
    async def in_listener_loop(self) -> None:
        """Update status for chirp."""
        htchirp_tools.chirp_status("Listening for incoming tasks")

    @with_basic_housekeeping
    async def queue_housekeeping(
        self,
        in_queue: mq.Queue,
        sub: mq.queue.ManualQueueSubResource,
        pub: mq.queue.QueuePubResource,
    ) -> None:
        """Do housekeeping for queue + basic housekeeping."""

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

    @with_basic_housekeeping
    async def exited_listener_loop(self) -> None:
        """Update status for chirp."""
        htchirp_tools.chirp_status("Done listening for incoming tasks")

    @with_basic_housekeeping
    async def message_recieved(self, total_msg_count: int) -> None:
        """Update message count for chirp."""
        if total_msg_count == 1:
            htchirp_tools.chirp_status("Tasking")
        htchirp_tools.chirp_new_total(total_msg_count)

    @with_basic_housekeeping
    async def new_messages_done(self, n_success: int, n_failed: int) -> None:
        """Update done counts for chirp."""
        htchirp_tools.chirp_new_failed_total(n_failed)
        htchirp_tools.chirp_new_success_total(n_success)

    @with_basic_housekeeping
    async def waiting_for_remaining_tasks(self) -> None:
        """Update status for chirp."""
        htchirp_tools.chirp_status("Waiting for remaining tasks")

    @with_basic_housekeeping
    async def done_tasking(self) -> None:
        """Update status for chirp."""
        htchirp_tools.chirp_status("Done with all tasks")
