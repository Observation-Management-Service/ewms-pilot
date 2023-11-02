"""Logic for running a subprocess."""


import asyncio
import shlex
import shutil
import sys
from pathlib import Path
from typing import Optional, TextIO

from ..config import LOGGER


def get_last_line(fpath: Path) -> str:
    """Get the last line of the file."""
    with fpath.open() as f:
        line = ""
        for line in f:
            pass
        return line.rstrip()  # remove trailing '\n'


class PilotSubprocessError(Exception):
    """Raised when the subprocess terminates in an error."""

    def __init__(self, return_code: int, stderrfile: Path):
        super().__init__(
            f"Subprocess completed with exit code {return_code}: "
            f"{get_last_line(stderrfile)}"
        )


def mv_or_rm_file(src: Path, dest: Optional[Path]) -> None:
    """Move the file to `dest` if not None, else rm it.

    No error if file doesn't exist.
    """
    if not src.exists():
        return
    if dest:
        # src.rename(dest / src.name)  # mv
        # NOTE: https://github.com/python/cpython/pull/30650
        shutil.move(str(src), str(dest / src.name))  # py 3.6 requires strs
    else:
        src.unlink()  # rm


def _dump_binary_file(fpath: Path, stream: TextIO) -> None:
    try:
        with open(fpath, "rb") as file:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                stream.buffer.write(chunk)
    except Exception as e:
        LOGGER.error(f"Error dumping subprocess output ({stream.name}): {e}")


async def run_subproc(
    cmd: str,
    subproc_timeout: Optional[int],
    stdoutfile: Path,
    stderrfile: Path,
    dump_output: bool,
) -> None:
    """Start a subprocess running `cmd`."""

    # call & check outputs
    LOGGER.info(f"Executing: {shlex.split(cmd)}")
    try:
        with open(stdoutfile, "wb") as stdoutf, open(stderrfile, "wb") as stderrf:
            # await to start & prep coroutines
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=stdoutf,
                stderr=stderrf,
            )
            # await to finish
            try:
                await asyncio.wait_for(  # raises TimeoutError
                    proc.wait(),
                    timeout=subproc_timeout,
                )
            except (TimeoutError, asyncio.exceptions.TimeoutError) as e:
                # < 3.11 -> asyncio.exceptions.TimeoutError
                raise TimeoutError(
                    f"subprocess timed out after {subproc_timeout}s"
                ) from e

        LOGGER.info(f"Subprocess return code: {proc.returncode}")

        # exception handling (immediately re-handled by 'except' below)
        if proc.returncode:
            raise PilotSubprocessError(proc.returncode, stderrfile)

    except Exception as e:
        LOGGER.error(f"Subprocess failed: {e}")  # log the time
        raise
    finally:
        if dump_output:
            _dump_binary_file(stdoutfile, sys.stdout)
            _dump_binary_file(stderrfile, sys.stderr)
