"""Single task logic."""


import asyncio
import shlex
import shutil
from pathlib import Path
from typing import Any, Callable, Optional

from mqclient.broker_client_interface import Message

from .config import LOGGER
from .utils import FileType


def get_last_line(fpath: Path) -> str:
    """Get the last line of the file."""
    with fpath.open() as f:
        line = ""
        for line in f:
            pass
        return line.rstrip()  # remove trailing '\n'


class TaskSubprocessError(Exception):
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


async def process_msg_task(
    in_msg: Message,
    cmd: str,
    task_timeout: Optional[int],
    #
    ftype_to_subproc: FileType,
    ftype_from_subproc: FileType,
    #
    file_writer: Callable[[Any, Path], None],
    file_reader: Callable[[Path], Any],
    #
    staging_dir: Path,
    keep_debug_dir: bool,
) -> Any:
    """Process the message's task in a subprocess using `cmd` & respond."""

    # staging-dir logic
    staging_subdir = staging_dir / str(in_msg.uuid)
    staging_subdir.mkdir(parents=True, exist_ok=False)
    stderrfile = staging_subdir / "stderrfile"
    stdoutfile = staging_subdir / "stdoutfile"

    # create in/out filepaths
    infilepath = staging_subdir / f"in-{in_msg.uuid}{ftype_to_subproc.value}"
    outfilepath = staging_subdir / f"out-{in_msg.uuid}{ftype_from_subproc.value}"

    # insert in/out files into cmd
    cmd = cmd.replace("{{INFILE}}", str(infilepath))
    cmd = cmd.replace("{{OUTFILE}}", str(outfilepath))

    # write message for subproc
    file_writer(in_msg.data, infilepath)

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
            await asyncio.wait_for(  # raises TimeoutError
                proc.wait(),
                timeout=task_timeout,
            )

        LOGGER.info(f"Subprocess return code: {proc.returncode}")

        # exception handling (immediately re-handled by 'except' below)
        if proc.returncode:
            raise TaskSubprocessError(proc.returncode, stderrfile)

    # Error Case: first, if there's a file move it to debug dir (if enabled)
    except Exception as e:
        LOGGER.error(f"Subprocess failed: {e}")  # log the time
        raise

    # Successful Case: get message and move to debug dir
    out_data = file_reader(outfilepath)

    # send
    LOGGER.info("Sending return message...")

    # cleanup -- on success only
    if not keep_debug_dir:
        shutil.rmtree(staging_subdir)  # rm -r

    return out_data
