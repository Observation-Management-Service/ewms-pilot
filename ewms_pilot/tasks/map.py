"""A mapping for EWMS messages, asyncio io tasks, etc."""

import asyncio
import dataclasses as dc
import time

from mqclient.broker_client_interface import Message


@dc.dataclass
class TaskMapping:
    """A mapping for EWMS messages, asyncio io tasks, etc."""

    message: Message
    asyncio_task: asyncio.Task

    start_time: float
    end_time: float = 0.0

    # just b/c the asyncio_task may be done, doesn't mean this object is done
    is_done: bool = False

    # could be the asyncio task exception or an error from downstream handling
    error: BaseException | None = None

    def mark_done(self) -> None:
        """Mark the task done and update attrs."""
        if self.is_done:
            raise RuntimeError("Attempted to mark an already-done task as done.")
        self.is_done = True
        self.end_time = time.time()

    @property
    def is_pending(self) -> bool:
        """Check if the EWMS task is pending.

        Just b/c the asyncio_task may be no longer pending, doesn't mean this object is.
        """
        return not self.is_done

    @staticmethod
    def get(
        task_maps: list["TaskMapping"],
        /,
        asyncio_task: asyncio.Task | None = None,
    ) -> "TaskMapping":
        """Retrieves the object mapped with the given asyncio task."""
        return next(tm for tm in task_maps if tm.asyncio_task == asyncio_task)

    @staticmethod
    def n_pending(task_maps: list["TaskMapping"]) -> int:
        """Returns the number of pending tasks."""
        return len([tm for tm in task_maps if tm.is_pending])

    @staticmethod
    def n_done(task_maps: list["TaskMapping"]) -> int:
        """Returns the number of done tasks."""
        return len([tm for tm in task_maps if tm.is_done])

    @staticmethod
    def n_successful(task_maps: list["TaskMapping"]) -> int:
        """Returns the number of successful tasks."""
        return len([tm for tm in task_maps if tm.is_done and not tm.error])

    @staticmethod
    def n_failed(task_maps: list["TaskMapping"]) -> int:
        """Returns the number of failed tasks."""
        return len([tm for tm in task_maps if tm.is_done and tm.error])
