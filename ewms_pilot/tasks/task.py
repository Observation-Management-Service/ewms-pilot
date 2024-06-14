"""Single task logic."""

import shutil
from pathlib import Path
from typing import Any, Optional

from mqclient.broker_client_interface import Message

from ..config import LOGGER
from ..utils.subproc import run_subproc


async def process_msg_task(
    in_msg: Message,
    cmd: str,
    task_timeout: Optional[int],
    #
    ftype_to_subproc: str,
    ftype_from_subproc: str,
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

    # create in/out filepaths
    infilepath = staging_subdir / f"in-{in_msg.uuid}.{ftype_to_subproc.lstrip('.')}"
    outfilepath = staging_subdir / f"out-{in_msg.uuid}.{ftype_from_subproc.lstrip('.')}"

    # insert in/out files into cmd
    cmd = cmd.replace("{{INFILE}}", str(infilepath))
    cmd = cmd.replace("{{OUTFILE}}", str(outfilepath))

    # run
    with open(infilepath) as f:
        f.write(in_msg.data)
    await run_subproc(cmd, task_timeout, stdoutfile, stderrfile, dump_task_output)
    with open(outfilepath) as f:
        out_data = f.read()

    # send
    LOGGER.info("Sending return message...")

    # cleanup -- on success only
    if not keep_debug_dir:
        shutil.rmtree(staging_subdir)  # rm -r

    return out_data
