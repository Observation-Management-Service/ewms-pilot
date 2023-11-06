"""Tools for communicating with HTChirp."""


import enum
import sys
import time
import traceback
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

import htchirp  # type: ignore[import]
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
    """Set the job attr along with an additional attr with a timestamp.

    If there's an exception chirping, log it and silently continue.
    """

    def _set_job_attr(_name: str, _val: Any) -> None:
        LOGGER.info(f"HTChirp ({ctx.whoami()}) -> {_name} = {_val}")
        if isinstance(_val, (int, float, bool)):  # (non-str) built-in types
            ctx.set_job_attr(_name, str(_val))
        else:
            ctx.set_job_attr(_name, f'"{str(_val)}"')

    try:
        _set_job_attr(attr.name, value)
        _set_job_attr(f"{attr.name}_Timestamp", int(time.time()))
    except Exception as e:
        LOGGER.error("chirping failed")
        LOGGER.exception(e)


def _is_chirp_enabled() -> bool:
    if not ENV.EWMS_PILOT_HTCHIRP:
        return False

    try:  # check if ".chirp.config" is present / provided a host and port
        htchirp.HTChirp()
    except ValueError:
        return False

    return True


def chirp_status(status_message: str) -> None:
    """Invoke HTChirp, AKA send a status message to Condor."""
    if not _is_chirp_enabled():
        return

    if not status_message:
        return

    with htchirp.HTChirp() as c:
        chirp_job_attr(c, HTChirpAttr.HTChirpEWMSPilotStatus, status_message)


def chirp_new_total(total: int) -> None:
    """Send a Condor Chirp signalling a new total of tasks handled."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        chirp_job_attr(c, HTChirpAttr.HTChirpEWMSPilotTasksTotal, total)


def chirp_new_success_total(total: int) -> None:
    """Send a Condor Chirp signalling a new total of succeeded task(s)."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        chirp_job_attr(c, HTChirpAttr.HTChirpEWMSPilotTasksSuccess, total)


def chirp_new_failed_total(total: int) -> None:
    """Send a Condor Chirp signalling a new total of failed task(s)."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        chirp_job_attr(c, HTChirpAttr.HTChirpEWMSPilotTasksFailed, total)


def initial_chirp() -> None:
    """Send a Condor Chirp signalling that processing has started."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        chirp_job_attr(c, HTChirpAttr.HTChirpEWMSPilotStarted, True)


def error_chirp(exception: Exception) -> None:
    """Send a Condor Chirp signalling that processing ran into an error."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        chirp_job_attr(
            c,
            HTChirpAttr.HTChirpEWMSPilotError,
            f"{type(exception).__name__}: {exception}",
        )

        if sys.version_info >= (3, 10):
            chirp_job_attr(
                c,
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
                c,
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
            error_chirp(e)
            raise

    return wrapper
