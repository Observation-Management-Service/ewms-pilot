"""Single task logic."""

import logging
import shutil
from pathlib import Path
from typing import Any, Optional

from mqclient.broker_client_interface import Message

from .io import FileExtension, InFileInterface, OutFileInterface
from ..utils.runner import run_container

LOGGER = logging.getLogger(__name__)


async def process_msg_task(
    in_msg: Message,
    #
    task_image: str,
    task_args: str,
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

    # staging-dir logic -- includes stderr/stdout files (see below)
    task_staging_dpath = staging_dir / str(in_msg.uuid)
    task_staging_dpath.mkdir(parents=True, exist_ok=False)

    # msgs dpath(s) -- make this separate so container only has access to message(s)
    msgs_dpath = task_staging_dpath / "msgs"
    msgs_dpath.mkdir(parents=True, exist_ok=False)
    msgs_dpath_inside_container = Path("/ewms-pilot/task-io/")

    # create in/out filepaths -- piggy-back the uuid since it's unique and trackable
    infilepath = msgs_dpath / f"infile-{in_msg.uuid}.{infile_ext}"
    outfilepath = msgs_dpath / f"outfile-{in_msg.uuid}.{outfile_ext}"

    # insert in/out files into task_args
    task_args = task_args.replace(
        "{{INFILE}}",
        str(msgs_dpath_inside_container / infilepath.name),
    )
    task_args = task_args.replace(
        "{{OUTFILE}}",
        str(msgs_dpath_inside_container / outfilepath.name),
    )

    # do task
    InFileInterface.write(in_msg, infilepath)
    await run_container(
        task_image,
        task_args,
        task_timeout,
        task_staging_dpath / "stderrfile",
        task_staging_dpath / "stdoutfile",
        dump_task_output,
        f"--mount type=bind,source={msgs_dpath.resolve()},target={msgs_dpath_inside_container}",
    )
    out_data = OutFileInterface.read(outfilepath)

    # send
    LOGGER.info("Sending response message...")

    # cleanup -- on success only
    if not keep_debug_dir:
        shutil.rmtree(task_staging_dpath)  # rm -r

    return out_data
