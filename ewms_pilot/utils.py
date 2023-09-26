"""Common utilities."""


from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

import htchirp  # type: ignore[import]
from typing_extensions import ParamSpec

from .config import ENV, LOGGER

T = TypeVar("T")
P = ParamSpec("P")


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

    with htchirp.HTChirp() as c:
        LOGGER.info(f"chirping as '{c.whoami()}'")
        c.set_job_attr("EWMSPilotProcessing", "True")
        if status_message:
            c.set_job_attr("EWMSPilotStatus", status_message)
            c.ulog(status_message)


def _initial_chirp() -> None:
    """Send a Condor Chirp signalling that processing has started."""
    chirp_status("")


def _final_chirp(error: bool = False) -> None:
    """Send a Condor Chirp signalling that processing has started."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        LOGGER.info(f"chirping as '{c.whoami()}'")
        c.set_job_attr("EWMSPilotSucess", str(not error))


def error_chirp(exception: Exception) -> None:
    """Send a Condor Chirp signalling that processing ran into an error."""
    if not _is_chirp_enabled():
        return

    with htchirp.HTChirp() as c:
        LOGGER.info(f"chirping as '{c.whoami()}'")
        exception_str = f"{type(exception).__name__}: {exception}"
        c.set_job_attr("EWMSPilotError", exception_str)
        c.ulog(exception_str)


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
