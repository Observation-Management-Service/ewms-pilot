"""Common utilities."""

import json
import logging
import re
from pathlib import Path

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


class NoLogsInFileException(Exception):
    """Raised when there are no logs in a log file."""


class LogParser:
    """A parser for stderr logfiles."""

    # ex:
    # DEBUG   [U=59925,P=1]      SomeFunction()            Some log message
    # VERBOSE [U=613,P=42]       AnotherFunc()             Another log entry
    APPTAINER_LOG_PATTERN = re.compile(r"^[A-Z]+\s+\[U=\d+,P=\d+\]\s+")

    def __init__(self, log_fpath: Path):
        self.log_fpath = log_fpath

    def _get_nonblank_lines(self) -> list[str]:
        with open(self.log_fpath, "r", encoding="utf-8") as file:
            # no new-lines, no blank lines
            lines = [ln.rstrip("\n") for ln in file.readlines() if ln.strip()]
        if not lines:
            LOGGER.info("No lines in log file.")
            raise NoLogsInFileException()
        return lines

    def _get_last_non_apptainer_logline_index(self) -> int | None:
        lines = self._get_nonblank_lines()
        for i, line in enumerate(reversed(lines)):
            if not self.APPTAINER_LOG_PATTERN.match(line):
                return len(lines) - (i + 1)  # previous line's index
        return None  # aka it's all apptainer log lines

    def apptainer_extract_error(self) -> str:
        """Extracts the most relevant error message from a log file which includes Apptainer logs.

        Priority order:
        1. A Python traceback (if present).
        2. The first non-Apptainer error.
        3. The last Apptainer log entry, if nothing else is found.

        Returns:
            str: The most relevant error message found.
        """
        LOGGER.info(f"Extracting Apptainer logs from log file ({self.log_fpath})...")

        # prep
        try:
            lines = self._get_nonblank_lines()
        except NoLogsInFileException:
            LOGGER.info("No lines in log file.")
            return "<no stderr logs>"

        # Step 1: Locate the last error line before apptainer log line
        last_non_apptainer_index = self._get_last_non_apptainer_logline_index()

        # Step 2: Is there any actual good info here, or was this all apptainer logs?
        #
        # Example: "Child exited with exit status 255"
        # DEBUG   [U=613,P=1]        sylogBuiltin()                Running action command run
        # FATAL   [U=613,P=1]        StageTwo()                    exec /bin/bash failed: fork/exec /bin/bash: input/output error
        # DEBUG   [U=613,P=47]       startContainer()              stage 2 process reported an error, waiting status
        # DEBUG   [U=613,P=47]       CleanupContainer()            Cleanup container
        # DEBUG   [U=613,P=47]       umount()                      Umount /var/lib/apptainer/mnt/session/final
        # DEBUG   [U=613,P=47]       umount()                      Umount /var/lib/apptainer/mnt/session/rootfs
        # DEBUG   [U=613,P=47]       Master()                      Child exited with exit status 255
        # <EOF>
        if last_non_apptainer_index is None:  # still None b/c only saw apptainer logs
            LOGGER.info("Log file only contains apptainer logs--using the final one.")
            # return the very last line, parsed
            try:
                return "[Apptainer-Error] " + " ".join(
                    # Extract message
                    lines[-1].split(maxsplit=3)[3:]
                )
            except IndexError:
                LOGGER.warning(
                    f"failed to further parse error from apptainer-level log line "
                    f"(now, using whole line instead): {lines[-1]}"
                )
                return lines[-1]

        return self._extract_error(last_non_apptainer_index)

    def generic_extract_error(self) -> str:
        """Extracts the most relevant error message from a log file."""
        return self._extract_error(None)

    def _extract_error(self, last_line_index: int | None) -> str:
        """Extracts the most relevant error message from a log file.

        'last_line_index' controls how far to look into file (iow don't look at very end).
        """
        LOGGER.info(f"Extracting logs from log file ({self.log_fpath})...")

        # prep
        try:
            lines = self._get_nonblank_lines()
        except NoLogsInFileException:
            LOGGER.info("No lines in log file.")
            return "<no stderr logs>"
        if last_line_index is None:
            last_line_index = len(lines) - 1  # the actual last line

        # Step 1: Check for a Python traceback, then use that
        #
        # Example 1:
        # ...
        # Traceback (most recent call last):
        #   File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
        #     return _run_code(code, main_globals, None,
        #   File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
        #     exec(code, run_globals)
        # ...
        #   File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/client/reco_icetray.py", line 151, in reco_pixel
        #     reco.setup_reco()
        #   File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/recos/millipede_wilks.py", line 73, in setup_reco
        #     self.cascade_service = photonics_service.I3PhotoSplineService(
        # RuntimeError: Error reading table coefficients
        # <other lines skipped b/c 'last_line_index'>
        # <EOF>
        #
        # Example 2:
        # ...
        # Traceback (most recent call last):
        #   File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
        #   File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
        # ...
        #   File "<frozen importlib._bootstrap_external>", line 1016, in get_code
        #   File "<frozen importlib._bootstrap_external>", line 1073, in get_data
        # OSError: [Errno 107] Transport endpoint is not connected: '/usr/lib/python3/dist-packages/pandas/core/arrays/sparse/array.py'
        # <other lines skipped b/c 'last_line_index'>
        # <EOF>
        potential_python_traceback: list[str] = []
        for line in reversed(lines[: last_line_index + 1]):
            potential_python_traceback.insert(0, line)
            if line.startswith("Traceback"):  # Start of traceback found
                LOGGER.info("Logs contain a python traceback--using final traceback.")
                return "\n".join(potential_python_traceback)

        # ELSE: If no traceback, return last non-Apptainer error
        #
        # Example: "curl: (22) The requested URL returned error: 404"
        # ...
        # curl: (22) The requested URL returned error: 404
        # <other lines skipped b/c 'last_line_index'>
        # <EOF>
        LOGGER.info(
            f"Using {'last line' if last_line_index == len(lines) - 1 else f'line #{last_line_index}'}."
        )
        return lines[last_line_index]
