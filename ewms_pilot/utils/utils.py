"""Common utilities."""

import json
import logging
import statistics

from ewms_pilot.tasks.map import TaskMapping

LOGGER = logging.getLogger(__name__)


def all_task_errors_string(task_errors: list[BaseException]) -> str:
    """Make a string from the multiple task exceptions."""
    for exception in task_errors:
        LOGGER.error(exception)
    return (
        f"{len(task_errors)} TASK(S) FAILED: "
        f"{', '.join(repr(e) for e in task_errors)}"
    )


def dump_task_stats(task_maps: list[TaskMapping]) -> None:
    """Dump stats about the given task maps."""
    LOGGER.info("Task runtime stats:")

    LOGGER.info(
        json.dumps(
            [
                {
                    "start": tm.start_time,
                    "end": tm.end_time,
                    "runtime": tm.end_time - tm.start_time,
                    "done": tm.is_done,
                    "error": bool(tm.error),
                }
                for tm in task_maps
            ],
            indent=4,
        )
    )

    runtimes = [tmap.end_time - tmap.start_time for tmap in task_maps if tmap.is_done]
    if not runtimes:
        LOGGER.info("no finished tasks")
        return

    LOGGER.info(f"Task runtime min: {min(runtimes):.3f} seconds")
    LOGGER.info(f"Task runtime max: {max(runtimes):.3f} seconds")
    LOGGER.info(f"Task runtime mean: {statistics.mean(runtimes):.3f} seconds")
    LOGGER.info(f"Task runtime median: {statistics.median(runtimes):.3f} seconds")
