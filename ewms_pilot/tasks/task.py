"""Single task logic."""

import logging
from typing import Any

from mqclient.broker_client_interface import Message

from .io import (
    FileExtension,
    InFileInterface,
    NoTaskResponseException,
    OutFileInterface,
)
from ..config import (
    ENV,
    InTaskContainerEnvVarNames,
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
    dirs.outputs_on_pilot.mkdir(parents=True, exist_ok=False)
    dirs.task_io.on_pilot.mkdir(parents=True, exist_ok=False)

    # create in/out file *names* -- piggy-back the uuid since it's unique and trackable
    infile_name = f"infile-{in_msg.uuid}.{infile_ext}"
    outfile_name = f"outfile-{in_msg.uuid}.{outfile_ext}"

    # do task
    InFileInterface.write(in_msg, dirs.task_io.on_pilot / infile_name)
    in_container_infile = str(dirs.task_io.in_task_container / infile_name)
    in_container_outfile = str(dirs.task_io.in_task_container / outfile_name)
    await task_runner.run_container(
        dirs.outputs_on_pilot / "stderrfile",
        dirs.outputs_on_pilot / "stdoutfile",
        dirs.assemble_bind_mounts(external_directories=True, task_io=True),
        {
            InTaskContainerEnvVarNames.EWMS_TASK_DATA_HUB_DIR.name: dirs.pilot_data_hub.in_task_container,
            InTaskContainerEnvVarNames.EWMS_TASK_INFILE.name: in_container_infile,
            InTaskContainerEnvVarNames.EWMS_TASK_OUTFILE.name: in_container_outfile,
        },
        infile_arg_replacement=in_container_infile,
        outfile_arg_replacement=in_container_outfile,
    )

    # get outfile response
    try:
        return OutFileInterface.read(dirs.task_io.on_pilot / outfile_name)
    except NoTaskResponseException as e:
        LOGGER.info(str(e))
        raise  # don't return `None` b/c that could be a valid response value
    # cleanup
    finally:
        if not ENV.EWMS_PILOT_KEEP_ALL_TASK_FILES:
            dirs.rm_unique_dirs()
