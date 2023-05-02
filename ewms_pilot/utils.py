"""Common utilities."""


from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

import htchirp  # type: ignore[import]
from typing_extensions import ParamSpec

from .config import LOGGER

T = TypeVar("T")
P = ParamSpec("P")


def chirp_status(status_message: str) -> None:
    """Invoke HTChirp, AKA send a status message to Condor."""
    try:
        chirper = htchirp.HTChirp()
    except ValueError:  # ".chirp.config must be present or you must provide a host and port
        return

    with chirper as c:
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
    try:
        chirper = htchirp.HTChirp()
    except ValueError:  # ".chirp.config must be present or you must provide a host and port"
        return

    with chirper as c:
        LOGGER.info(f"chirping as '{c.whoami()}'")
        c.set_job_attr("EWMSPilotSucess", str(not error))


def error_chirp(exception: Exception) -> None:
    """Send a Condor Chirp signalling that processing ran into an error."""
    try:
        chirper = htchirp.HTChirp()
    except ValueError:  # ".chirp.config must be present or you must provide a host and port
        return

    with chirper as c:
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
