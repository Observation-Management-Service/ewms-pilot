"""A mapping for EWMS messages, asyncio io tasks, etc."""

import asyncio
import dataclasses as dc

from mqclient.broker_client_interface import Message


@dc.dataclass
class TaskMapping:
    """A mapping for EWMS messages, asyncio io tasks, etc."""

    message: Message
    asyncio_task: asyncio.Task

    start_time: float
    end_time: float = 0.0
    error: str = ""

    @staticmethod
    def get(
        task_maps: list["TaskMapping"],
        /,
        asyncio_task: asyncio.Task | None = None,
    ) -> "TaskMapping":
        """Retrieves the object mapped with the given asyncio task."""
        return next(tm for tm in task_maps if tm.asyncio_task == asyncio_task)
