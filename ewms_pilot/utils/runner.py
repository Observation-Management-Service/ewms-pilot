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

from ..config import ENV, PILOT_DATA_DIR, PILOT_DATA_HUB_DIR_NAME

LOGGER = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------


# Regular expression to detect Apptainer log lines in the format: "<string><space>[<no spaces>]<space>*"
APPTAINER_PATTERN = re.compile(r"^\S+\s+\[[^\s]+\]\s+")
CLEANUP_PATTERN = re.compile(r"^DEBUG\s+\[.*\]\s+CleanupContainer\(\)")


def extract_error_from_log(log_file_path: Path) -> str:
    """Extracts the most relevant error message from a log file.

    The function prioritizes:
    1. A Python traceback, if present.
    2. The first non-Apptainer error **before CleanupContainer()**, if applicable.
    3. The first non-Apptainer error.
    4. The last Apptainer log entry, if no other errors are found.

    Args:
        log_file_path (Path): Path to the log file.

    Returns:
        str: The most relevant error message found in the log.
    """
    with open(log_file_path, "r", encoding="utf-8") as file:
        # no new-lines, no blank lines
        lines = [ln.rstrip("\n") for ln in file.readlines() if ln.strip()]

    if not lines:
        return "<no error info>"

    # find index of "CleanupContainer()" line
    revstart_index = len(lines) - 1  # fallback val: aka start at the end
    for i, line in enumerate(lines):
        if CLEANUP_PATTERN.match(line):
            revstart_index = i - 1  # aka start on the line before
            break

    last_nonapptainer_line = lines[revstart_index]

    # is there any actual good info here, or was this an apptainer error?
    #
    # Example:
    # ...
    # DEBUG   [U=613,P=47]       startContainer()              stage 2 process reported an error, waiting status
    # DEBUG   [U=613,P=47]       CleanupContainer()            Cleanup container
    # DEBUG   [U=613,P=47]       umount()                      Umount /var/lib/apptainer/mnt/session/final
    # DEBUG   [U=613,P=47]       umount()                      Umount /var/lib/apptainer/mnt/session/rootfs
    # DEBUG   [U=613,P=47]       Master()                      Child exited with exit status 255
    if APPTAINER_PATTERN.match(last_nonapptainer_line):
        # return the very last line
        return lines[-1]  # TODO: remove cols 1 & 2

    # at this point, we may be looking at a python stacktrace
    #
    # Example 1:
    # ...
    # Traceback (most recent call last):
    #   File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    #     return _run_code(code, main_globals, None,
    #   File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
    #     exec(code, run_globals)
    #   File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/client/__main__.py", line 7, in <module>
    #     reco_icetray.main()
    #   File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/client/reco_icetray.py", line 299, in main
    #     reco_pixel(
    #   File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/client/reco_icetray.py", line 151, in reco_pixel
    #     reco.setup_reco()
    #   File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/recos/millipede_wilks.py", line 73, in setup_reco
    #     self.cascade_service = photonics_service.I3PhotoSplineService(
    # RuntimeError: Error reading table coefficients
    # DEBUG   [U=59925,P=95]     CleanupContainer()            Cleanup container
    # DEBUG   [U=59925,P=95]     umount()                      Umount /var/lib/apptainer/mnt/session/final
    # DEBUG   [U=59925,P=95]     umount()                      Umount /var/lib/apptainer/mnt/session/rootfs
    # DEBUG   [U=59925,P=95]     Master()                      Child exited with exit status 1
    #
    # Example 2:
    # ...
    # Traceback (most recent call last):
    #   File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
    #   File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
    #   File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/client/__main__.py", line 3, in <module>
    #   File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/client/reco_icetray.py", line 29, in <module>
    #   File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/utils/load_scan_state.py", line 12, in <module>
    #   File "/usr/local/lib/python3.10/dist-packages/skyreader/__init__.py", line 3, in <module>
    #   File "/usr/local/lib/python3.10/dist-packages/skyreader/plot/__init__.py", line 1, in <module>
    #   File "/usr/local/lib/python3.10/dist-packages/skyreader/plot/plot.py", line 30, in <module>
    #   File "/usr/local/lib/python3.10/dist-packages/skyreader/utils/handle_map_data.py", line 8, in <module>
    #   File "/usr/local/lib/python3.10/dist-packages/skyreader/result.py", line 19, in <module>
    #   File "/usr/lib/python3/dist-packages/pandas/__init__.py", line 56, in <module>
    #   File "/usr/lib/python3/dist-packages/pandas/core/api.py", line 29, in <module>
    #   File "/usr/lib/python3/dist-packages/pandas/core/arrays/__init__.py", line 11, in <module>
    #   File "/usr/lib/python3/dist-packages/pandas/core/arrays/interval.py", line 82, in <module>
    #   File "/usr/lib/python3/dist-packages/pandas/core/indexes/base.py", line 90, in <module>
    #   File "/usr/lib/python3/dist-packages/pandas/core/dtypes/concat.py", line 26, in <module>
    #   File "/usr/lib/python3/dist-packages/pandas/core/arrays/sparse/__init__.py", line 3, in <module>
    #   File "/usr/lib/python3/dist-packages/pandas/core/arrays/sparse/accessor.py", line 13, in <module>
    #   File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
    #   File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
    #   File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
    #   File "<frozen importlib._bootstrap_external>", line 879, in exec_module
    #   File "<frozen importlib._bootstrap_external>", line 1016, in get_code
    #   File "<frozen importlib._bootstrap_external>", line 1073, in get_data
    # OSError: [Errno 107] Transport endpoint is not connected: '/usr/lib/python3/dist-packages/pandas/core/arrays/sparse/array.py'
    # DEBUG   [U=59925,P=94]     CleanupContainer()            Cleanup container
    # DEBUG   [U=59925,P=94]     umount()                      Umount /var/lib/apptainer/mnt/session/final
    # DEBUG   [U=59925,P=94]     umount()                      Umount /var/lib/apptainer/mnt/session/rootfs
    # DEBUG   [U=59925,P=94]     Master()                      Child exited with exit status 1
    potential_python_traceback = []
    for line in reversed(lines[: revstart_index + 1]):
        potential_python_traceback.insert(0, line)
        if line.startswith("Traceback"):  # got to the start of the traceback!
            return "\n".join(potential_python_traceback)
    # no, it was not a python traceback

    # back up plan: grab last non-blank line
    #
    # Example:
    # ...
    # curl: (22) The requested URL returned error: 404
    # DEBUG   [U=30101,P=1]      StartProcess()                Received signal child exited
    # DEBUG   [U=30101,P=49]     CleanupContainer()            Cleanup container
    # DEBUG   [U=30101,P=49]     umount()                      Umount /var/lib/apptainer/mnt/session/final
    # DEBUG   [U=30101,P=49]     umount()                      Umount /var/lib/apptainer/mnt/session/rootfs
    # DEBUG   [U=30101,P=49]     Master()                      Child exited with exit status 22
    return last_nonapptainer_line


class ContainerRunError(Exception):
    """Raised when the container terminates in an error."""

    def __init__(self, return_code: int, error_string: str, image: str):
        super().__init__(
            f"Container completed with exit code {return_code}: "
            f"'{error_string}' "
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
                    proc.returncode,
                    extract_error_from_log(stderrfile),
                    self.image,
                )

        except Exception as e:
            LOGGER.error(f"Subprocess failed: {e}")  # log the time
            dump_output = True
            raise
        finally:
            if dump_output:
                _dump_binary_file(stdoutfile, sys.stdout)
                _dump_binary_file(stderrfile, sys.stderr)
