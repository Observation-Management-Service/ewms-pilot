"""Tools for running an init container."""

import asyncio
import logging
import uuid

from .. import htchirp_tools
from ..config import ENV, InTaskContainerEnvVarNames, REFRESH_INTERVAL
from ..housekeeping import Housekeeping
from ..utils.runner import ContainerRunner, DirectoryCatalog

LOGGER = logging.getLogger(__name__)


@htchirp_tools.async_htchirp_error_wrapper
async def run_init_container(
    init_runner: ContainerRunner,
    housekeeper: Housekeeping,
) -> None:
    """Run the init container with the given arguments."""
    await housekeeper.running_init_container()

    dirs = DirectoryCatalog(f"init-{uuid.uuid4().hex}")

    task = asyncio.create_task(
        init_runner.run_container(
            dirs.outputs_on_pilot / "stdoutfile",
            dirs.outputs_on_pilot / "stderrfile",
            dirs.assemble_bind_mounts(external_directories=True),
            {
                InTaskContainerEnvVarNames.EWMS_TASK_DATA_HUB_DIR.name: dirs.pilot_data_hub.in_task_container,
            },
            datahub_arg_replacement=str(dirs.pilot_data_hub.in_task_container),
        )
    )
    pending = set([task])

    # wait with housekeeping
    while pending:
        _, pending = await asyncio.wait(
            pending,
            return_when=asyncio.ALL_COMPLETED,
            timeout=REFRESH_INTERVAL,
        )
        await housekeeper.basic_housekeeping()

    # see if the task failed
    try:
        await task
    except Exception as e:
        LOGGER.exception(e)
        raise

    # cleanup -- on success only
    if not ENV.EWMS_PILOT_KEEP_ALL_TASK_FILES:
        dirs.rm_unique_dirs()

    await housekeeper.finished_init_command()
