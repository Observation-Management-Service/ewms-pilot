"""Single task logic."""

import shutil
from pathlib import Path
from typing import Optional, Any

from mqclient.broker_client_interface import Message

from .io import FileExtension, InFileInterface, OutFileInterface
from ..config import LOGGER
from ..utils.subproc import run_subproc


async def process_msg_task(
    in_msg: Message,
    cmd: str,
    task_timeout: Optional[int],
    #
    infile_ext: FileExtension,
    outfile_ext: FileExtension,
    #
    staging_dir: Path,
    keep_debug_dir: bool,
    dump_task_output: bool,
) -> Any:
    """Process the message's task in a subprocess using `cmd` & respond."""

    # staging-dir logic
    staging_subdir = staging_dir / str(in_msg.uuid)
    staging_subdir.mkdir(parents=True, exist_ok=False)
    stderrfile = staging_subdir / "stderrfile"
    stdoutfile = staging_subdir / "stdoutfile"

    # create in/out filepaths -- piggy-back the uuid since it's unique and trackable
    infilepath = staging_subdir / f"infile-{in_msg.uuid}.{infile_ext}"
    outfilepath = staging_subdir / f"outfile-{in_msg.uuid}.{outfile_ext}"

    # insert in/out files into cmd
    cmd = cmd.replace("{{INFILE}}", str(infilepath))
    cmd = cmd.replace("{{OUTFILE}}", str(outfilepath))

    InFileInterface.write(in_msg, infilepath)
    await run_subproc(cmd, task_timeout, stdoutfile, stderrfile, dump_task_output)
    out_data = OutFileInterface.read(outfilepath)

    # send
    LOGGER.info("Sending response message...")

    # cleanup -- on success only
    if not keep_debug_dir:
        shutil.rmtree(staging_subdir)  # rm -r

    return out_data
