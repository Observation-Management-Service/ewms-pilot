"""Tools for communicating with HTChirp."""

import asyncio
import enum
import logging
import sys
import time
import traceback
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

import htchirp  # type: ignore[import-untyped]
from htcondor import classad  # type: ignore[import-untyped]
from typing_extensions import ParamSpec

from .config import ENV

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")


class PilotStatus(enum.Enum):
    """A simple listing of statuses, useful for reporting & aggregation."""

    Started = enum.auto()
    RunningInitCommand = enum.auto()
    AwaitingFirstMessage = enum.auto()
    Tasking = enum.auto()
    PendingRemainingTasks = enum.auto()

    FatalError = enum.auto()
    Done = enum.auto()


class HTChirpAttr(enum.Enum):
    """Organized list of attributes for chirping."""

    HTChirpEWMSPilotLastUpdatedTimestamp = enum.auto()  # auto-set by backlog

    HTChirpEWMSPilotStartedTimestamp = enum.auto()
    HTChirpEWMSPilotStatus = enum.auto()

    HTChirpEWMSPilotTasksTotal = enum.auto()
    HTChirpEWMSPilotTasksFailed = enum.auto()
    HTChirpEWMSPilotTasksSuccess = enum.auto()

    HTChirpEWMSPilotError = enum.auto()
    HTChirpEWMSPilotErrorTraceback = enum.auto()


def _chirp(ctx: htchirp.HTChirp, _attr: HTChirpAttr, _val: Any) -> None:
    """Chirp to either a job attr (default) or the job event log."""

    # Use job log
    if ENV.EWMS_PILOT_HTCHIRP_DEST == "JOB_EVENT_LOG":
        # classad.quote escape new-lines, etc.
        job_log_line = f"{_attr.name}: {classad.quote(str(_val))}"
        LOGGER.info(job_log_line)
        ctx.ulog(job_log_line)
    # Use job attribute
    elif ENV.EWMS_PILOT_HTCHIRP_DEST == "JOB_ATTR":
        # condor has built-in types (see below for strs)
        if isinstance(_val, (int, float)):
            # https://htcondor.readthedocs.io/en/latest/classads/classad-mechanism.html#composing-literals
            job_attr_val = str(_val)
        else:
            job_attr_val = classad.quote(str(_val))
        LOGGER.info(job_attr_val)
        ctx.set_job_attr(_attr.name, job_attr_val)
    # ???
    else:
        raise ValueError(
            f"Invalid EWMS_PILOT_HTCHIRP_DEST: {ENV.EWMS_PILOT_HTCHIRP_DEST}"
        )


class Chirper:
    """Handle htchirp connection(s) and sending."""

    def __init__(self) -> None:
        self._conn = None
        self._backlog: dict[HTChirpAttr, Any] = {}
        self._last_backlog_time = 0.0

    def _get_conn(self) -> htchirp.HTChirp:
        """Get chirp object, (re)establishing the connection if needed."""
        if self._conn:
            return self._conn

        try:  # checks if ".chirp.config" is present / provided a host and port
            self._conn = htchirp.HTChirp()
            self._conn.__enter__()  # type: ignore[attr-defined]
            return self._conn
        except Exception as e:
            LOGGER.error(f"HTChirp not available ({type(e).__name__}: {e})")
            raise

    def _reset_conn(self) -> None:
        self.close()

    def close(self, *args: Any) -> None:
        """Close the connection with the Chirp server."""
        if not self._conn:
            return
        try:
            self._conn.__exit__(*args)
        except Exception as e:
            LOGGER.error("chirping exit failed")
            LOGGER.exception(e)
        finally:
            self._conn = None

    async def chirp_backlog_until_done(self, total_time: int, sleep: int) -> float:
        """Call `chirp_backlog()` until backlog is all sent successfully.

        Total time may take a little bit longer than `total_time`,
        depending on the `sleep` value and the runtime of `chirp_backlog()`.

        Return the amount of time leftover from `total_time`.
        """
        if not ENV.EWMS_PILOT_HTCHIRP:
            return total_time

        start = time.time()

        while True:
            self.chirp_backlog()
            if (not self._backlog) or (time.time() - start >= total_time):
                break
            await asyncio.sleep(sleep)

        return max(0.0, total_time - (time.time() - start))  # remainder

    def chirp_backlog(self, is_rate_limited: bool = False) -> None:
        """Set all job attrs plus an additional attr -- a timestamp."""
        if not ENV.EWMS_PILOT_HTCHIRP:
            return

        if is_rate_limited and (
            time.time() - self._last_backlog_time
            < ENV.EWMS_PILOT_HTCHIRP_RATELIMIT_INTERVAL
        ):
            return

        # set HTChirpEWMSPilotLastUpdatedTimestamp & verify backlog
        self._backlog.pop(HTChirpAttr.HTChirpEWMSPilotLastUpdatedTimestamp, None)
        if not self._backlog:
            return  # nothing to chirp
        now = int(time.time())
        self._backlog[HTChirpAttr.HTChirpEWMSPilotLastUpdatedTimestamp] = now

        # chirp it all
        try:
            conn = self._get_conn()
            for bl_attr, bl_value in list(self._backlog.items()):
                _chirp(conn, bl_attr, bl_value)
                self._backlog.pop(bl_attr)  # wait to remove until success
        except Exception as e:
            LOGGER.error("chirping failed")
            LOGGER.exception(e)
            self._reset_conn()
        else:
            self._last_backlog_time = time.time()  # wait to set until all success

    def chirp_status(self, status: PilotStatus) -> None:
        """Invoke HTChirp, AKA send a status message to Condor."""
        if status == PilotStatus.Started:
            self._backlog[HTChirpAttr.HTChirpEWMSPilotStartedTimestamp] = int(
                time.time()
            )

        self._backlog[HTChirpAttr.HTChirpEWMSPilotStatus] = status.name
        self.chirp_backlog()

    def chirp_new_total(self, total: int) -> None:
        """Send a Condor Chirp signalling a new total of tasks handled.

        This chirp is enqueued (rate limited) and sent every X seconds.
        """
        if not total:
            # total can only increase -> can be inferred total=0 if attr is absent
            return

        self._backlog[HTChirpAttr.HTChirpEWMSPilotTasksTotal] = total
        self.chirp_backlog(is_rate_limited=True)

    def chirp_new_success_total(self, total: int) -> None:
        """Send a Condor Chirp signalling a new total of succeeded task(s).

        This chirp is enqueued (rate limited) and sent every X seconds.
        """
        if not total:
            # total can only increase -> can be inferred total=0 if attr is absent
            return

        self._backlog[HTChirpAttr.HTChirpEWMSPilotTasksSuccess] = total
        self.chirp_backlog(is_rate_limited=True)

    def chirp_new_failed_total(self, total: int) -> None:
        """Send a Condor Chirp signalling a new total of failed task(s).

        This chirp is enqueued (rate limited) and sent every X seconds.
        """
        if not total:
            # total can only increase -> can be inferred total=0 if attr is absent
            return

        self._backlog[HTChirpAttr.HTChirpEWMSPilotTasksFailed] = total
        self.chirp_backlog(is_rate_limited=True)

    def initial_chirp(self) -> None:
        """Send a Condor Chirp signalling that processing has started."""
        self.chirp_status(PilotStatus.Started)

    def error_chirp(self, exception: Exception) -> None:
        """Send a Condor Chirp signalling that processing ran into an error."""
        str_error = f"{type(exception).__name__}: {exception}"
        self._backlog[HTChirpAttr.HTChirpEWMSPilotError] = str_error

        if sys.version_info >= (3, 10):
            str_traceback = "".join(traceback.format_exception(exception))
        else:  # backwards compatibility
            # grabbed this from `logging.Logger._log()`
            if isinstance(exception, BaseException):
                exc_info = (type(exception), exception, exception.__traceback__)
            else:
                exc_info = sys.exc_info()
            str_traceback = "".join(traceback.format_exception(*exc_info))
        self._backlog[HTChirpAttr.HTChirpEWMSPilotErrorTraceback] = str_traceback

        self.chirp_backlog()


def async_htchirp_error_wrapper(
    func: Callable[P, Coroutine[Any, Any, T]]
) -> Callable[P, Coroutine[Any, Any, T]]:
    """Send Condor Chirp of any raised non-excepted exception."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            ret = await func(*args, **kwargs)
            return ret
        except Exception as e:
            chirper = Chirper()
            chirper.error_chirp(e)
            chirper.close()
            raise

    return wrapper
