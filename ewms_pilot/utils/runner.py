"""Logic for running a subprocess."""

import asyncio
import dataclasses as dc
import json
import logging
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TextIO

from .utils import LogParser
from ..config import (
    BIND_MOUNT_IN_CONTAINER_READONLY_DIRS,
    BIND_MOUNT_ON_PILOT_FORBIDDEN_DIRS,
    BIND_MOUNT_ON_PILOT_READONLY_DIRS,
    ENV,
    PILOT_DATA_DIR,
    PILOT_DATA_HUB_DIR_NAME,
)

LOGGER = logging.getLogger(__name__)

ENV_VAR_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# --------------------------------------------------------------------------------------


class ContainerSetupError(Exception):
    """Exception raised when a container pre-run actions fail."""

    def __init__(self, message: str, useful_identifier: str):
        """`useful_identifier` can be image name, task id, etc."""
        super().__init__(f"{message} for {useful_identifier}")


class ContainerRunError(Exception):
    """Raised when the container terminates in an error."""

    def __init__(
        self,
        alias: str,
        error_string: str,
        exit_code: int | None = None,
    ):
        exit_str = f" (exit code {exit_code})" if exit_code is not None else ""
        super().__init__(f"{alias} failed{exit_str}: {error_string}")


class InvalidBindMountError(Exception):
    """Raised when a bind mount is invalid."""


# --------------------------------------------------------------------------------------


@dc.dataclass
class ContainerBindMount:
    """A validated bind mount from host (on_pilot) to container (in_task_container)."""

    on_pilot: Path
    in_task_container: Path
    is_readonly: bool = False

    def __post_init__(self):
        for fpath in (self.on_pilot, self.in_task_container):
            if not fpath.is_absolute():
                raise InvalidBindMountError(
                    f"Bind mount path must be absolute: {fpath}"
                )

        if not self.on_pilot.is_dir():
            raise InvalidBindMountError(
                f"Bind mount does not exist on pilot: {self.on_pilot}"
            )

        # Disallow all access to forbidden host paths
        for forbidden in BIND_MOUNT_ON_PILOT_FORBIDDEN_DIRS:
            if self.on_pilot.resolve(strict=True).is_relative_to(forbidden):
                raise InvalidBindMountError(
                    f"Refusing to bind mount forbidden host path: {self.on_pilot}"
                )

        if not self.is_readonly:
            # Disallow writable mounts from read-only-only paths
            for readonly_only in BIND_MOUNT_ON_PILOT_READONLY_DIRS:
                if self.on_pilot.resolve(strict=True).is_relative_to(readonly_only):
                    raise InvalidBindMountError(
                        f"Refusing to bind mount writable host path: {self.on_pilot}"
                    )
            # Disallow writing into sensitive container paths
            for sensitive in BIND_MOUNT_IN_CONTAINER_READONLY_DIRS:
                if self.in_task_container.is_relative_to(sensitive):
                    raise InvalidBindMountError(
                        f"Refusing to mount writable directory to sensitive container path: {self.in_task_container}"
                    )


class DirectoryCatalog:
    """Handles the naming and mapping logic for a task's directories."""

    def __init__(self, name: str, include_task_io_directory: bool):
        """All directories are auto-created (task_io dir cannot already exist)."""
        self.name = name
        self._namebased_dir = PILOT_DATA_DIR / self.name

        def _mkdir(_fpath: Path, exist_ok=True) -> Path:
            _fpath.mkdir(parents=True, exist_ok=exist_ok)
            return _fpath

        # for inter-task/init storage: startup data, init container's output, etc.
        self.pilot_data_hub = ContainerBindMount(
            _mkdir(PILOT_DATA_DIR / PILOT_DATA_HUB_DIR_NAME),
            Path(f"/{PILOT_DATA_DIR.name}/{PILOT_DATA_HUB_DIR_NAME}"),
        )

        # for persisting stderr and stdout
        self.outputs_on_pilot = _mkdir(self._namebased_dir / "outputs")

        # for message-based task i/o
        if include_task_io_directory:
            self.task_io: ContainerBindMount | None = ContainerBindMount(
                _mkdir(self._namebased_dir / "task-io", exist_ok=False),
                Path(f"/{PILOT_DATA_DIR.name}/task-io"),
            )
        else:
            self.task_io = None

    def assemble_bind_mounts(
        self,
        include_external_directories: bool = False,
    ) -> list[ContainerBindMount]:
        """Get the docker bind mount string containing the wanted directories."""
        bind_mounts: list[ContainerBindMount] = [
            self.pilot_data_hub,
        ]

        if include_external_directories:
            bind_mounts.extend(
                ContainerBindMount(Path(d), Path(d), is_readonly=True)
                for d in ENV.EWMS_PILOT_EXTERNAL_DIRECTORIES.split(",")
                if d  # skip any blanks
            )

        if self.task_io:
            bind_mounts.append(self.task_io)

        targets = [m.in_task_container for m in bind_mounts]
        if len(set(targets)) != len(targets):
            raise ContainerSetupError(
                "Duplicate container mount targets detected",
                self.name,
            )

        return bind_mounts

    def rm_unique_dirs(self) -> None:
        """Remove all directories (on host) created for use only by this container."""
        shutil.rmtree(self._namebased_dir)  # rm -r


# --------------------------------------------------------------------------------------


def _dump_binary_file(fpath: Path, stream: TextIO, name: str) -> None:
    start_line = f"--- start: {name} ({stream.name}) "
    end_line = f"--- end: {name} ({stream.name}) "
    try:
        stream.write(start_line.ljust(60, "-") + "\n")
        stream.flush()
        with open(fpath, "rb") as file:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                stream.buffer.write(chunk)
        stream.write(end_line.ljust(60, "-") + "\n")
        stream.flush()
    except Exception as e:
        LOGGER.error(f"Error dumping container output ({stream.name}): {e}")


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
            # NOTE: there is additional validation before execution--the more validation, the better
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
                _run(
                    #
                    # NOTE: validate & sanitize values HERE--this is the point of no return!
                    #       (making calls here makes it very clear what is checked)
                    #
                    f"docker pull "
                    f"{shlex.quote(image)}",
                )
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
                    #
                    # NOTE: validate & sanitize values HERE--this is the point of no return!
                    #       (making calls here makes it very clear what is checked)
                    #
                    # cd b/c want to *build* in a directory w/ enough space (intermediate files)
                    f"cd {ENV._EWMS_PILOT_APPTAINER_BUILD_WORKDIR} && "
                    f"apptainer "
                    f"{'--debug ' if ENV.EWMS_PILOT_CONTAINER_DEBUG else ''}"
                    f"build "
                    f"--fix-perms "
                    f"--sandbox {shlex.quote(dir_image)} "
                    f"{shlex.quote(image)}"
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

    def _validate_env_var_name(self, name: str) -> str:
        if not ENV_VAR_NAME_RE.match(name):
            raise ContainerSetupError(
                f"Invalid environment variable name: {name}",
                self.image,
            )
        return name

    def _validate_env_var_value_to_str(self, value: str) -> str:
        if not isinstance(value, (str | int | Path)):
            raise ContainerSetupError(
                f"Invalid environment variable value (not str or int): '{value}'",
                self.image,
            )
        return str(value)

    async def run_container(
        self,
        logging_alias: str,  # what to call this container for logging and error-reporting
        stdoutfile: Path,
        stderrfile: Path,
        bind_mounts: list[ContainerBindMount],
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

        # assemble command
        # NOTE: don't add to bind_mounts (WYSIWYG); also avoid intermediate structures
        match ENV._EWMS_PILOT_CONTAINER_PLATFORM.lower():
            case "docker":
                cmd = (
                    #
                    # NOTE: validate & sanitize values HERE--this is the point of no return!
                    #       (making calls here makes it very clear what is checked)
                    #
                    f"docker run --rm "
                    # optional
                    f"{f'--shm-size={ENV._EWMS_PILOT_DOCKER_SHM_SIZE} ' if ENV._EWMS_PILOT_DOCKER_SHM_SIZE else ''}"
                    # bind mounts
                    f"{" ".join(
                        f"--mount type=bind,"
                        f"source={shlex.quote(str(m.on_pilot))},"
                        f"target={shlex.quote(str(m.in_task_container))}"
                        f"{',readonly' if m.is_readonly else ''}"
                        for m in bind_mounts
                    )} "  # <- space
                    # env vars
                    f"{" ".join(
                        f"--env "
                        f"{self._validate_env_var_name(n)}="
                        f"{shlex.quote(self._validate_env_var_value_to_str(v))}"
                        for n, v in sorted((self.env | env_as_dict).items())
                        # in case of key conflicts, choose the vals specific to this run
                    )} "  # <- space
                    # image + args
                    f"{shlex.quote(self.image)} "
                    f"{' '.join(shlex.quote(a) for a in shlex.split(inst_args))}"
                )
            case "apptainer":
                cmd = (
                    #
                    # NOTE: validate & sanitize values HERE--this is the point of no return!
                    #       (making calls here makes it very clear what is checked)
                    #
                    f"apptainer "
                    f"{'--debug ' if ENV.EWMS_PILOT_CONTAINER_DEBUG else ''}"
                    f"run "
                    # always add these flags
                    f"--containall "  # don't auto-mount anything
                    f"--no-eval "  # don't interpret CL args
                    # bind mounts
                    f"{" ".join(
                        f"--mount type=bind,"
                        f"source={shlex.quote(str(m.on_pilot))},"
                        f"target={shlex.quote(str(m.in_task_container))}"
                        f"{',readonly' if m.is_readonly else ''}"
                        for m in bind_mounts
                    )} "  # <- space
                    # env vars
                    f"{" ".join(
                        f"--env "
                        f"{self._validate_env_var_name(n)}="
                        f"{shlex.quote(self._validate_env_var_value_to_str(v))}"
                        for n, v in sorted((self.env | env_as_dict).items())
                        # in case of key conflicts, choose the vals specific to this run
                    )} "  # <- space
                    # image + args
                    f"{shlex.quote(self.image)} "
                    f"{' '.join(shlex.quote(a) for a in shlex.split(inst_args))}"
                )
            case other:
                raise ValueError(
                    f"'_EWMS_PILOT_CONTAINER_PLATFORM' is not a supported value: {other} ({logging_alias})"
                )
        LOGGER.info(f"Running {logging_alias} command: {cmd}")

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
                    raise ContainerRunError(
                        logging_alias,
                        f"[Timeout-Error] timed out after {self.timeout}s",
                    ) from e

            LOGGER.info(f"{logging_alias} return code: {proc.returncode}")

            # exception handling (immediately re-handled by 'except' below)
            if proc.returncode:
                log_parser = LogParser(stderrfile)
                raise ContainerRunError(
                    logging_alias,
                    (
                        log_parser.apptainer_extract_error()
                        if ENV._EWMS_PILOT_CONTAINER_PLATFORM.lower() == "apptainer"
                        else log_parser.generic_extract_error()
                    ),
                    exit_code=proc.returncode,
                )

        except Exception as e:
            LOGGER.error(f"{logging_alias} failed: {e}")  # log the time
            dump_output = True
            raise
        finally:
            if dump_output:
                _dump_binary_file(stdoutfile, sys.stdout, logging_alias)
                _dump_binary_file(stderrfile, sys.stderr, logging_alias)
