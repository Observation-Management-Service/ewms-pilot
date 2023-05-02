"""Common utilities."""


from typing import Awaitable, Callable, TypeVar

import htchirp  # type: ignore[import]
from typing_extensions import ParamSpec

from .config import LOGGER

T = TypeVar("T")
P = ParamSpec("P")


def chirp(message: str) -> None:
    """Invoke HTChirp, AKA send a status message to Condor."""
    try:
        chirper = htchirp.HTChirp()
    except ValueError:  # ".chirp.config must be present or you must provide a host and port
        return

    with chirper as c:
        LOGGER.info(f"chirping as '{c.whoami()}'")
        c.set_job_attr("EWMSPilotProcessing", "True")
        if message:
            c.ulog(message)


def _initial_chirp() -> None:
    """Send a Condor Chirp signalling that processing has started."""
    chirp("")


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
        c.set_job_attr("EWMSPilotError", "True")
        c.ulog(f"{type(exception).__name__}: {exception}")


def async_htchirping(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """Send Condor Chirps at start, end, and if needed, final error."""

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
