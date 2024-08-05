"""Single task logic."""

import logging
from typing import Any

from mqclient.broker_client_interface import Message

from .io import FileExtension, InFileInterface, OutFileInterface
from ..config import (
    ENV,
    INCONTAINER_ENVNAME_TASK_DATA_HUB_DIR,
)
from ..utils.runner import ContainerRunner, DirectoryCatalog

LOGGER = logging.getLogger(__name__)


async def process_msg_task(
    in_msg: Message,
    #
    task_runner: ContainerRunner,
    #
    infile_ext: FileExtension,
    outfile_ext: FileExtension,
) -> Any:
    """Process the message's task in a subprocess using `cmd` & respond."""

    # staging-dir logic -- includes stderr/stdout files (see below)
    dirs = DirectoryCatalog(str(in_msg.uuid))
    dirs.outputs_on_host.mkdir(parents=True, exist_ok=False)
    dirs.task_io.on_host.mkdir(parents=True, exist_ok=False)

    # create in/out file *names* -- piggy-back the uuid since it's unique and trackable
    infile_name = f"infile-{in_msg.uuid}.{infile_ext}"
    outfile_name = f"outfile-{in_msg.uuid}.{outfile_ext}"

    # do task
    InFileInterface.write(in_msg, dirs.task_io.on_host / infile_name)
    await task_runner.run_container(
        dirs.outputs_on_host / "stderrfile",
        dirs.outputs_on_host / "stdoutfile",
        dirs.assemble_bind_mounts(external_directories=True, task_io=True),
        f"--env {INCONTAINER_ENVNAME_TASK_DATA_HUB_DIR}={dirs.pilot_data_hub.in_container}",
        infile_arg_replacement=str(dirs.task_io.in_container / infile_name),
        outfile_arg_replacement=str(dirs.task_io.in_container / outfile_name),
    )
    out_data = OutFileInterface.read(dirs.task_io.on_host / outfile_name)

    # send
    LOGGER.info("Sending response message...")

    # cleanup -- on success only
    if not ENV.EWMS_PILOT_KEEP_ALL_TASK_FILES:
        dirs.rm_unique_dirs()

    return out_data
