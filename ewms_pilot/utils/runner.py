"""Logic for running a subprocess."""

import asyncio
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


async def run_container(
    image: str,
    args: str,
    timeout: Optional[int],
    stdoutfile: Path,
    stderrfile: Path,
    dump_output: bool,
    mount_bindings: str = "",
) -> None:
    """Run the container and dump outputs."""
    cmd = f"docker run --rm -i {mount_bindings} {image} {args}"
    LOGGER.info(cmd)

    # call & check outputs
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
                    timeout=timeout,
                )
            except (TimeoutError, asyncio.exceptions.TimeoutError) as e:
                # < 3.11 -> asyncio.exceptions.TimeoutError
                raise TimeoutError(f"subprocess timed out after {timeout}s") from e

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
