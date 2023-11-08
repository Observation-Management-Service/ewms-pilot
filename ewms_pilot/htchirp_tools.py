"""Tools for communicating with HTChirp."""


import enum
import sys
import time
import traceback
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

import htchirp  # type: ignore[import]
from htcondor import classad  # type: ignore[import]
from typing_extensions import ParamSpec

from .config import ENV, LOGGER

T = TypeVar("T")
P = ParamSpec("P")


class HTChirpAttr(enum.Enum):
    """Organized list of attributes for chirping."""

    # pylint:disable=invalid-name
    HTChirpEWMSPilotStarted = enum.auto()
    HTChirpEWMSPilotStatus = enum.auto()

    HTChirpEWMSPilotTasksTotal = enum.auto()
    HTChirpEWMSPilotTasksFailed = enum.auto()
    HTChirpEWMSPilotTasksSuccess = enum.auto()

    HTChirpEWMSPilotError = enum.auto()
    HTChirpEWMSPilotErrorTraceback = enum.auto()


def chirp_job_attr(ctx: htchirp.HTChirp, attr: HTChirpAttr, value: Any) -> None:
    """Set the job attr along with an additional attr with a timestamp."""

    def _set_job_attr(_name: str, _val: Any) -> None:
        LOGGER.info(f"HTChirp ({ctx.whoami()}) -> {_name} = {_val}")
        # condor has built-in types (see below for strs)
        if isinstance(_val, (int, float)):
            # https://htcondor.readthedocs.io/en/latest/classads/classad-mechanism.html#composing-literals
            ctx.set_job_attr(_name, str(_val))
        else:
            ctx.set_job_attr(_name, classad.quote(str(_val)))

    _set_job_attr(attr.name, value)
    _set_job_attr(f"{attr.name}_Timestamp", int(time.time()))


def _reset_conn_on_exception(func: Callable[P, None]) -> Callable[P, None]:
    """Suppress any exception, then log it and reset the chirp connection."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            func(*args, **kwargs)
        except Exception as e:
            LOGGER.error("chirping failed")
            LOGGER.exception(e)
            args[0]._reset_conn()  # type: ignore[attr-defined]

    return wrapper


class Chirper:
    """Handle htchirp connection(s) and sending."""

    def __init__(self) -> None:
        self._conn = None

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

    @_reset_conn_on_exception
    def chirp_status(self, status_message: str) -> None:
        """Invoke HTChirp, AKA send a status message to Condor."""
        if not ENV.EWMS_PILOT_HTCHIRP:
            return

        if not status_message:
            return

        chirp_job_attr(
            self._get_conn(),
            HTChirpAttr.HTChirpEWMSPilotStatus,
            status_message,
        )

    @_reset_conn_on_exception
    def chirp_new_total(self, total: int) -> None:
        """Send a Condor Chirp signalling a new total of tasks handled."""
        if not ENV.EWMS_PILOT_HTCHIRP:
            return

        chirp_job_attr(
            self._get_conn(),
            HTChirpAttr.HTChirpEWMSPilotTasksTotal,
            total,
        )

    @_reset_conn_on_exception
    def chirp_new_success_total(self, total: int) -> None:
        """Send a Condor Chirp signalling a new total of succeeded task(s)."""
        if not ENV.EWMS_PILOT_HTCHIRP:
            return

        chirp_job_attr(
            self._get_conn(),
            HTChirpAttr.HTChirpEWMSPilotTasksSuccess,
            total,
        )

    @_reset_conn_on_exception
    def chirp_new_failed_total(self, total: int) -> None:
        """Send a Condor Chirp signalling a new total of failed task(s)."""
        if not ENV.EWMS_PILOT_HTCHIRP:
            return

        chirp_job_attr(
            self._get_conn(),
            HTChirpAttr.HTChirpEWMSPilotTasksFailed,
            total,
        )

    @_reset_conn_on_exception
    def initial_chirp(self) -> None:
        """Send a Condor Chirp signalling that processing has started."""
        if not ENV.EWMS_PILOT_HTCHIRP:
            return

        chirp_job_attr(
            self._get_conn(),
            HTChirpAttr.HTChirpEWMSPilotStarted,
            True,
        )

    @_reset_conn_on_exception
    def error_chirp(self, exception: Exception) -> None:
        """Send a Condor Chirp signalling that processing ran into an error."""
        if not ENV.EWMS_PILOT_HTCHIRP:
            return

        chirp_job_attr(
            self._get_conn(),
            HTChirpAttr.HTChirpEWMSPilotError,
            f"{type(exception).__name__}: {exception}",
        )

        if sys.version_info >= (3, 10):
            chirp_job_attr(
                self._get_conn(),
                HTChirpAttr.HTChirpEWMSPilotErrorTraceback,
                "".join(traceback.format_exception(exception)),
            )
        else:  # backwards compatibility
            # grabbed this from `logging.Logger._log()`
            if isinstance(exception, BaseException):
                exc_info = (type(exception), exception, exception.__traceback__)
            else:
                exc_info = sys.exc_info()
            chirp_job_attr(
                self._get_conn(),
                HTChirpAttr.HTChirpEWMSPilotErrorTraceback,
                "".join(traceback.format_exception(*exc_info)),
            )


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
