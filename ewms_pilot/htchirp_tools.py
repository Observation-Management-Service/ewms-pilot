"""Tools for communicating with HTChirp."""


import enum
import time
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

    HTChirpEWMSPilotSucess = enum.auto()
    HTChirpEWMSPilotFailed = enum.auto()


def set_job_attr(ctx: htchirp.HTChirp, attr: HTChirpAttr, value: Any) -> None:
    """explain."""
    if isinstance(value, str):
        value = f'"{value}"'
    else:
        value = str(value)
    ctx.set_job_attr(attr.name, value)
    ctx.set_job_attr(f"{attr.name}_Timestamp", str(int(time.time())))


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
        LOGGER.info(f"chirping as '{c.whoami()}'")
        set_job_attr(c, HTChirpAttr.HTChirpEWMSPilotStatus, status_message)


def chirp_new_total(total: int) -> None:
    """Send a Condor Chirp signalling a new total of tasks handled."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        LOGGER.info(f"chirping as '{c.whoami()}'")
        set_job_attr(c, HTChirpAttr.HTChirpEWMSPilotTasksTotal, total)


def chirp_new_success_total(total: int) -> None:
    """Send a Condor Chirp signalling a new total of succeeded task(s)."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        LOGGER.info(f"chirping as '{c.whoami()}'")
        set_job_attr(c, HTChirpAttr.HTChirpEWMSPilotSucess, total)


def chirp_new_failed_total(total: int) -> None:
    """Send a Condor Chirp signalling a new total of failed task(s)."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        LOGGER.info(f"chirping as '{c.whoami()}'")
        set_job_attr(c, HTChirpAttr.HTChirpEWMSPilotFailed, total)


def _initial_chirp() -> None:
    """Send a Condor Chirp signalling that processing has started."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        LOGGER.info(f"chirping as '{c.whoami()}'")
        set_job_attr(c, HTChirpAttr.HTChirpEWMSPilotStarted, True)


def _final_chirp(error: bool = False) -> None:
    """Send a Condor Chirp signalling that processing has started."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        LOGGER.info(f"chirping as '{c.whoami()}'")
        set_job_attr(c, HTChirpAttr.HTChirpEWMSPilotSucess, not error)


def error_chirp(exception: Exception) -> None:
    """Send a Condor Chirp signalling that processing ran into an error."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        LOGGER.info(f"chirping as '{c.whoami()}'")
        set_job_attr(
            c,
            HTChirpAttr.HTChirpEWMSPilotFailed,
            f"{type(exception).__name__}: {exception}",
        )


def async_htchirping(
    func: Callable[P, Coroutine[Any, Any, T]]
) -> Callable[P, Coroutine[Any, Any, T]]:
    """Send Condor Chirps at start, end, and if needed, final error."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            _initial_chirp()
            ret = await func(*args, **kwargs)
            _final_chirp()
            return ret
        except Exception as e:
            error_chirp(e)
            _final_chirp(error=True)
            raise

    return wrapper
