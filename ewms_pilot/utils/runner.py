"""Logic for running a subprocess."""

import asyncio
import dataclasses as dc
import json
import logging
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TextIO

from ..config import ENV, PILOT_DATA_DIR, PILOT_DATA_HUB_DIR_NAME

LOGGER = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------


def get_last_nonblank_line(fpath: Path) -> str:
    """Get the last line of the file that is not entirely whitespace."""
    last_nonblank_line = ""
    with fpath.open() as f:
        for line in f:
            if stripped := line.strip():
                last_nonblank_line = stripped  # removed '\n' and anything else
        return last_nonblank_line


class ContainerRunError(Exception):
    """Raised when the container terminates in an error."""

    def __init__(self, return_code: int, last_line: str, image: str):
        super().__init__(
            f"Container completed with exit code {return_code}: "
            f"'{last_line}' "
            f"for {image}"
        )


# --------------------------------------------------------------------------------------


class DirectoryCatalog:
    """Handles the naming and mapping logic for a task's directories."""

    @dc.dataclass
    class _ContainerBindMountDirPair:
        on_pilot: Path
        in_task_container: Path

    def __init__(self, name: str):
        """All directories except the task-io dir is pre-created (mkdir)."""
        self._namebased_dir = PILOT_DATA_DIR / name

        # for inter-task/init storage: startup data, init container's output, etc.
        self.pilot_data_hub = self._ContainerBindMountDirPair(
            PILOT_DATA_DIR / PILOT_DATA_HUB_DIR_NAME,
            Path(f"/{PILOT_DATA_DIR.name}/{PILOT_DATA_HUB_DIR_NAME}"),
        )
        self.pilot_data_hub.on_pilot.mkdir(parents=True, exist_ok=True)

        # for persisting stderr and stdout
        self.outputs_on_pilot = self._namebased_dir / "outputs"
        self.outputs_on_pilot.mkdir(parents=True, exist_ok=False)

        # for message-based task i/o
        self.task_io = self._ContainerBindMountDirPair(
            self._namebased_dir / "task-io",
            Path(f"/{PILOT_DATA_DIR.name}/task-io"),
        )

    def assemble_bind_mounts(
        self,
        external_directories: bool = False,
        task_io: bool = False,
    ) -> str:
        """Get the docker bind mount string containing the wanted directories."""
        string = f"--mount type=bind,source={self.pilot_data_hub.on_pilot},target={self.pilot_data_hub.in_task_container} "

        if external_directories:
            string += "".join(
                f"--mount type=bind,source={dpath},target={dpath},readonly "
                for dpath in ENV.EWMS_PILOT_EXTERNAL_DIRECTORIES.split(",")
                if dpath  # skip any blanks
            )

        if task_io:
            string += f"--mount type=bind,source={self.task_io.on_pilot},target={self.task_io.in_task_container} "

        return string

    def rm_unique_dirs(self) -> None:
        """Remove all directories (on host) created for use only by this container."""
        shutil.rmtree(self._namebased_dir)  # rm -r


# --------------------------------------------------------------------------------------


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


class ContainerSetupError(Exception):
    """Exception raised when a container pre-run actions fail."""

    def __init__(self, message: str, image: str):
        super().__init__(f"{message} for {image}")


class ContainerRunner:
    """A utility class to run a container."""

    def __init__(
        self,
        image: str,
        args: str,
        timeout: int | None,
        env_json: str,
    ) -> None:
        self.args = args
        self.timeout = timeout
        self.image = self._prepull_image(image)

        if env := json.loads(env_json):
            LOGGER.debug(f"Validating env: {env}")
            if not isinstance(env, dict) and not all(
                isinstance(k, str) and isinstance(v, (str | int))
                for k, v in env.items()
            ):
                raise ContainerSetupError(
                    "container's env must be a string-dictionary of strings or ints",
                    image,
                )
        else:
            env = {}
        self.env = env

    @staticmethod
    def _prepull_image(image: str) -> str:
        """Pull the image so it can be used in many tasks.

        Return the fully-qualified image name.
        """
        LOGGER.info(f"Pulling image: {image}")

        def _run(cmd: str):
            LOGGER.info(f"Running command: {cmd}")
            try:
                ret = subprocess.run(
                    cmd,
                    capture_output=True,  # redirect stdout & stderr
                    text=True,  # outputs are strings
                    check=True,  # raise if error
                    shell=True,
                )
                print(ret.stdout)
                print(ret.stderr, file=sys.stderr)
            except subprocess.CalledProcessError as e:
                print(e.stdout)
                print(e.stderr, file=sys.stderr)
                last_line = e.stderr.split("\n")[-1]
                raise ContainerSetupError(f"{str(e)} [{last_line}]", image)

        match ENV._EWMS_PILOT_CONTAINER_PLATFORM.lower():

            case "docker":
                if ENV.CI:  # optimization during testing, images are *loaded* manually
                    LOGGER.warning(
                        f"The pilot is running in a test environment, "
                        f"skipping 'docker pull {image}' (env var CI=True)"
                    )
                    return image
                _run(f"docker pull {image}")
                return image

            # NOTE: We are only are able to run unpacked directory format on condor.
            #       Otherwise, we get error: `code 255: FATAL:   container creation
            #       failed: image driver mount failure: image driver squashfuse_ll
            #       instance exited with error: squashfuse_ll exited: fuse: device
            #       not found, try 'modprobe fuse' first`
            #       See https://github.com/Observation-Management-Service/ewms-pilot/pull/86
            case "apptainer":
                if Path(image).exists() and Path(image).is_dir():
                    LOGGER.info("OK: Apptainer image is already in directory format")
                    return image
                elif ENV._EWMS_PILOT_APPTAINER_IMAGE_DIRECTORY_MUST_BE_PRESENT:
                    # not directory and image-conversions are disallowed
                    raise ContainerSetupError(
                        "Image 'not found in filesystem and/or "
                        "cannot convert to apptainer directory (sandbox) format",
                        image,
                    )
                # CONVERT THE IMAGE
                # assume non-specified image is docker -- https://apptainer.org/docs/user/latest/build_a_container.html#overview
                if "." not in image and "://" not in image:
                    # is not a blah.sif file (or other) and doesn't point to a registry
                    image = f"docker://{image}"
                # name it something that is recognizable -- and put it where there is enough space
                dir_image = (
                    f"{ENV._EWMS_PILOT_APPTAINER_BUILD_WORKDIR}/"
                    f"{image.replace('://', '_').replace('/', '_')}/"
                )
                # build (convert)
                _run(
                    # cd b/c want to *build* in a directory w/ enough space (intermediate files)
                    f"cd {ENV._EWMS_PILOT_APPTAINER_BUILD_WORKDIR} && "
                    f"apptainer {'--debug ' if ENV.EWMS_PILOT_CONTAINER_DEBUG else ''}build "
                    f"--fix-perms "
                    f"--sandbox {dir_image} "
                    f"{image}"
                )
                LOGGER.info(
                    f"Image has been converted to Apptainer directory format: {dir_image}"
                )
                return dir_image

            # ???
            case other:
                raise ValueError(
                    f"'_EWMS_PILOT_CONTAINER_PLATFORM' is not a supported value: {other}"
                )

    async def run_container(
        self,
        stdoutfile: Path,
        stderrfile: Path,
        mount_bindings: str,
        env_as_dict: dict,
        infile_arg_replacement: str = "",
        outfile_arg_replacement: str = "",
        datahub_arg_replacement: str = "",
    ) -> None:
        """Run the container and dump outputs."""
        dump_output = ENV.EWMS_PILOT_DUMP_TASK_OUTPUT

        # insert arg placeholder replacements
        # -> give an alternative for each token replacement b/c it'd be a shame if
        #    things broke this late in the game
        inst_args = self.args
        if infile_arg_replacement:
            for token in ["{{INFILE}}", "{{IN_FILE}}"]:
                inst_args = inst_args.replace(token, infile_arg_replacement)
        if outfile_arg_replacement:
            for token in ["{{OUTFILE}}", "{{OUT_FILE}}"]:
                inst_args = inst_args.replace(token, outfile_arg_replacement)
        if datahub_arg_replacement:
            for token in ["{{DATA_HUB}}", "{{DATAHUB}}"]:
                inst_args = inst_args.replace(token, datahub_arg_replacement)

        # assemble env strings
        env_options = " ".join(
            f"--env {var}={shlex.quote(str(val))}"
            for var, val in (self.env | env_as_dict).items()
            # in case of key conflicts, choose the vals specific to this run
        )

        # assemble command
        # NOTE: don't add to mount_bindings (WYSIWYG); also avoid intermediate structures
        match ENV._EWMS_PILOT_CONTAINER_PLATFORM.lower():
            case "docker":
                cmd = (
                    f"docker run --rm "
                    # optional
                    f"{f'--shm-size={ENV._EWMS_PILOT_DOCKER_SHM_SIZE} ' if ENV._EWMS_PILOT_DOCKER_SHM_SIZE else ''}"
                    # provided options
                    f"{mount_bindings} "
                    f"{env_options} "
                    # image + args
                    f"{self.image} {inst_args}"
                )
            case "apptainer":
                cmd = (
                    f"apptainer {'--debug ' if ENV.EWMS_PILOT_CONTAINER_DEBUG else ''}run "
                    # always add these flags
                    f"--containall "  # don't auto-mount anything
                    f"--no-eval "  # don't interpret CL args
                    # provided options
                    f"{mount_bindings} "
                    f"{env_options} "
                    # image + args
                    f"{self.image} {inst_args}"
                )
            case other:
                raise ValueError(
                    f"'_EWMS_PILOT_CONTAINER_PLATFORM' is not a supported value: {other}"
                )
        LOGGER.info(f"Running command: {cmd}")

        # run: call & check outputs
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
                        timeout=self.timeout,
                    )
                except (TimeoutError, asyncio.exceptions.TimeoutError) as e:
                    # < 3.11 -> asyncio.exceptions.TimeoutError
                    raise TimeoutError(
                        f"subprocess timed out after {self.timeout}s"
                    ) from e

            LOGGER.info(f"Subprocess return code: {proc.returncode}")

            # exception handling (immediately re-handled by 'except' below)
            if proc.returncode:
                raise ContainerRunError(
                    proc.returncode, get_last_nonblank_line(stderrfile), self.image
                )

        except Exception as e:
            LOGGER.error(f"Subprocess failed: {e}")  # log the time
            dump_output = True
            raise
        finally:
            if dump_output:
                _dump_binary_file(stdoutfile, sys.stdout)
                _dump_binary_file(stderrfile, sys.stderr)
