"""Common utilities."""

import json
import logging

import numpy as np

from ewms_pilot.tasks.map import TaskMapping

LOGGER = logging.getLogger(__name__)


def all_task_errors_string(task_errors: list[BaseException]) -> str:
    """Make a string from the multiple task exceptions."""
    if not task_errors:
        return ""
    for exception in task_errors:
        LOGGER.error(exception)
    return (
        f"{len(task_errors)} TASK(S) FAILED: "
        f"{', '.join(repr(e) for e in task_errors)}"
    )


def dump_all_taskmaps(task_maps: list[TaskMapping]) -> None:
    """Dump all the task maps."""
    LOGGER.debug(
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


def dump_task_runtime_stats(task_maps: list[TaskMapping]) -> None:
    """Dump stats about the given task maps."""
    LOGGER.info("Task runtime stats (successful tasks):")

    runtimes = [
        tm.end_time - tm.start_time for tm in task_maps if tm.is_done and not tm.error
    ]
    if not runtimes:
        LOGGER.info("no finished successful tasks")
        return

    data_np = np.array(runtimes)

    # calculate statistics
    stats_summary = {
        "Count": len(runtimes),
        "Mean": np.mean(data_np),
        "Median": np.median(data_np),
        "Variance": np.var(data_np),
        "Standard Deviation": np.std(data_np),
        "Min": np.min(data_np),
        "Max": np.max(data_np),
        "Range": np.ptp(data_np),
    }
    for key, value in stats_summary.items():
        LOGGER.info(f"({key.lower()}: {value:.2f})")

    # make bins and a terminal-friendly chart
    LOGGER.info("Runtimes distribution:")
    hist, bin_edges = np.histogram(data_np, bins="auto")
    for i in range(len(hist)):
        bin_range = f"[{bin_edges[i]:.2f}, {bin_edges[i + 1]:.2f})"
        bar = "#" * hist[i]
        LOGGER.info(f"{bin_range:20} | {bar}")


def dump_tallies(task_maps: list[TaskMapping], dump_n_pending: bool = True) -> None:
    """Dump tallies about the given task maps."""
    string = ""
    if dump_n_pending:
        string += f"{TaskMapping.n_pending(task_maps)} Pending Tasks "
    string += (
        f"{TaskMapping.n_done(task_maps)} Finished Tasks "
        f"("
        f"{TaskMapping.n_successful(task_maps)} succeeded, "
        f"{TaskMapping.n_failed(task_maps)} failed"
        f")"
    )
    LOGGER.info(string)

    if _errors := [tm.error for tm in task_maps if tm.error]:
        LOGGER.error(all_task_errors_string(_errors))
