"""API for launching an MQ-task pilot."""


import argparse
import asyncio
import enum
import json
import pickle
import shlex
import shutil
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

import mqclient as mq
from mqclient.broker_client_interface import Message
from wipac_dev_tools import argparse_tools, logging_tools

from . import utils
from .config import ENV, LOGGER

AsyncioTaskMessages = Dict[asyncio.Task, Message]  # type: ignore[type-arg]


# if there's an error, have the cluster try again (probably a system error)
_EXCEPT_ERRORS = False

_DEFAULT_TIMEOUT_INCOMING = 1  # second
_DEFAULT_TIMEOUT_OUTGOING = 1  # second
_DEFAULT_PREFETCH = 1

# addl time to add to `mq.Queue.ack_timeout` for non-subproc activities
_ACK_TIMEOUT_NONSUBPROC_OVERHEAD_TIME = 10  # second  # this is more than enough


class FileType(enum.Enum):
    """Various file types/extensions."""

    PKL = ".pkl"
    TXT = ".txt"
    JSON = ".json"


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


def _task_exception_str(task: asyncio.Task) -> str:  # type: ignore[type-arg]
    return f"[{type(task.exception()).__name__}: {task.exception()}]"


class UniversalFileInterface:
    """Support reading and writing for any `FileType` file extension."""

    @classmethod
    def write(cls, in_msg: Any, fpath: Path) -> None:
        """Write `stuff` to `fpath` per `fpath.suffix`."""
        cls._write(in_msg, fpath)
        LOGGER.info(f"File Written :: {fpath} ({fpath.stat().st_size} bytes)")

    @classmethod
    def _write(cls, in_msg: Any, fpath: Path) -> None:
        LOGGER.info(f"Writing to file: {fpath}")
        LOGGER.debug(in_msg)

        # PKL
        if fpath.suffix == FileType.PKL.value:
            with open(fpath, "wb") as f:
                pickle.dump(in_msg, f)
        # TXT
        elif fpath.suffix == FileType.TXT.value:
            with open(fpath, "w") as f:
                f.write(in_msg)
        # JSON
        elif fpath.suffix == FileType.JSON.value:
            with open(fpath, "w") as f:
                json.dump(in_msg, f)
        # ???
        else:
            raise ValueError(f"Unsupported file type: {fpath.suffix} ({fpath})")

    @classmethod
    def read(cls, fpath: Path) -> Any:
        """Read and return contents of `fpath` per `fpath.suffix`."""
        msg = cls._read(fpath)
        LOGGER.info(f"File Read :: {fpath} ({fpath.stat().st_size} bytes)")
        LOGGER.debug(msg)
        return msg

    @classmethod
    def _read(cls, fpath: Path) -> Any:
        LOGGER.info(f"Reading from file: {fpath}")

        # PKL
        if fpath.suffix == FileType.PKL.value:
            with open(fpath, "rb") as f:
                return pickle.load(f)
        # TXT
        elif fpath.suffix == FileType.TXT.value:
            with open(fpath, "r") as f:
                return f.read()
        # JSON
        elif fpath.suffix == FileType.JSON.value:
            with open(fpath, "r") as f:
                return json.load(f)
        # ???
        else:
            raise ValueError(f"Unsupported file type: {fpath.suffix} ({fpath})")


def write_to_subproc(
    fpath_to_subproc: Path,
    in_msg: Any,
    debug_subdir: Optional[Path],
    file_writer: Callable[[Any, Path], None],
) -> Path:
    """Write the msg to the `IN` file.

    Also, dump to a file for debugging (if not "").
    """
    file_writer(in_msg, fpath_to_subproc)

    # persist the file?
    if debug_subdir:
        file_writer(in_msg, debug_subdir / fpath_to_subproc.name)

    return fpath_to_subproc


def mv_or_rm_file(src: Path, dest: Optional[Path]) -> None:
    """Move the file to `dest` if not None, else rm it.

    No error if file doesn't exist.
    """
    if not src.exists():
        return
    if dest:
        # src.rename(dest / src.name)  # mv
        # NOTE: https://github.com/python/cpython/pull/30650
        shutil.move(src, dest / src.name)
    else:
        src.unlink()  # rm


def read_from_subproc(
    fpath_from_subproc: Path,
    debug_subdir: Optional[Path],
    file_reader: Callable[[Path], Any],
) -> Any:
    """Read the msg from the `OUT` file.

    Also, dump to a file for debugging (if not "").
    """
    if not fpath_from_subproc.exists():
        msg = "Out-file cannot be found"
        LOGGER.error(msg)
        raise FileNotFoundError(msg)

    out_msg = file_reader(fpath_from_subproc)

    mv_or_rm_file(fpath_from_subproc, debug_subdir)

    return out_msg


async def process_msg_task(
    in_msg: Any,
    cmd: str,
    task_timeout: Optional[int],
    #
    ftype_to_subproc: FileType,
    ftype_from_subproc: FileType,
    #
    file_writer: Callable[[Any, Path], None],
    file_reader: Callable[[Path], Any],
    #
    debug_dir: Path,
    keep_debug_dir: bool,
    #
    pub: mq.queue.QueuePubResource,
) -> Any:
    """Process the message's task in a subprocess using `cmd` & respond."""
    task_id = uuid.uuid4().hex

    # debugging logic
    debug_subdir = debug_dir / task_id
    debug_subdir.mkdir(parents=True, exist_ok=False)
    stderrfile = debug_subdir / "stderrfile"
    stdoutfile = debug_subdir / "stdoutfile"

    # create in/out filepaths
    fpath_to_subproc = Path(f"in-{task_id}{ftype_to_subproc.value}")
    fpath_from_subproc = Path(f"out-{task_id}{ftype_from_subproc.value}")

    # insert in/out files into cmd
    cmd = cmd.replace("{{INFILE}}", str(fpath_to_subproc))
    cmd = cmd.replace("{{OUTFILE}}", str(fpath_from_subproc))

    # write
    write_to_subproc(fpath_to_subproc, in_msg, debug_subdir, file_writer)

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
        mv_or_rm_file(fpath_from_subproc, debug_subdir)
        raise

    # Successful Case: get message and move to debug dir
    out_msg = read_from_subproc(fpath_from_subproc, debug_subdir, file_reader)

    # send
    LOGGER.info("Sending return message...")
    await pub.send(out_msg)

    # cleanup -- on success only
    if not keep_debug_dir:
        shutil.rmtree(debug_subdir)  # rm -r


@utils.async_htchirping
async def consume_and_reply(
    cmd: str,
    #
    queue_incoming: str,
    queue_outgoing: str,
    #
    # for subprocess
    ftype_to_subproc: Union[str, FileType],
    ftype_from_subproc: Union[str, FileType],
    #
    # for mq
    broker_client: str = ENV.EWMS_PILOT_BROKER_CLIENT,
    broker_address: str = ENV.EWMS_PILOT_BROKER_ADDRESS,
    auth_token: str = ENV.EWMS_PILOT_BROKER_AUTH_TOKEN,
    #
    prefetch: int = _DEFAULT_PREFETCH,
    #
    timeout_wait_for_first_message: Optional[int] = None,
    timeout_incoming: int = _DEFAULT_TIMEOUT_INCOMING,
    timeout_outgoing: int = _DEFAULT_TIMEOUT_OUTGOING,
    #
    file_writer: Callable[[Any, Path], None] = UniversalFileInterface.write,
    file_reader: Callable[[Path], Any] = UniversalFileInterface.read,
    #
    debug_dir: Optional[Path] = None,
    #
    task_timeout: Optional[int] = ENV.EWMS_PILOT_TASK_TIMEOUT,
    quarantine_time: int = ENV.EWMS_PILOT_QUARANTINE_TIME,
    #
    multitasking: int = ENV.EWMS_PILOT_CONCURRENT_TASKS,
) -> None:
    """Communicate with server and outsource processing to subprocesses.

    Arguments:
        `timeout_wait_for_first_message`: if None, use 'timeout_incoming'
    """
    LOGGER.info("Making MQClient queue connections...")

    if not queue_incoming or not queue_outgoing:
        raise RuntimeError("Must define an incoming and an outgoing queue")

    ack_timeout = None
    if task_timeout:
        ack_timeout = task_timeout + _ACK_TIMEOUT_NONSUBPROC_OVERHEAD_TIME

    if not isinstance(ftype_to_subproc, FileType):
        ftype_to_subproc = FileType(ftype_to_subproc)
    if not isinstance(ftype_from_subproc, FileType):
        ftype_from_subproc = FileType(ftype_from_subproc)

    in_queue = mq.Queue(
        broker_client,
        address=broker_address,
        name=queue_incoming,
        prefetch=prefetch,
        auth_token=auth_token,
        except_errors=_EXCEPT_ERRORS,
        # timeout=timeout_incoming, # manually set below
        ack_timeout=ack_timeout,
    )
    out_queue = mq.Queue(
        broker_client,
        address=broker_address,
        name=queue_outgoing,
        auth_token=auth_token,
        except_errors=_EXCEPT_ERRORS,
        timeout=timeout_outgoing,
        ack_timeout=ack_timeout,
    )

    try:
        await _consume_and_reply(
            cmd,
            in_queue,
            out_queue,
            ftype_to_subproc,
            ftype_from_subproc,
            #
            timeout_wait_for_first_message,
            timeout_incoming,
            file_writer,
            file_reader,
            #
            debug_dir if debug_dir else Path("./tmp"),
            bool(debug_dir),
            #
            task_timeout,
            multitasking,
        )
    except Exception as e:
        if quarantine_time:
            msg = f"{e} (Quarantining for {quarantine_time} seconds)"
            utils.chirp_status(msg)
            LOGGER.error(msg)
            await asyncio.sleep(quarantine_time)
        raise


async def _ack_nack_finished_tasks(
    sub: mq.queue.ManualQueueSubResource,
    tasks: AsyncioTaskMessages,
    return_when: str,
    previous_failed: AsyncioTaskMessages,
) -> Tuple[AsyncioTaskMessages, AsyncioTaskMessages]:
    """Get finished tasks and ack/nack their messages.

    Returns:
        Tuple:
            AsyncioTaskMessages: pending tasks and
            AsyncioTaskMessages: failed tasks (plus those in `previous_failed`)
    """
    done, pending = await asyncio.wait(tasks.keys(), return_when=return_when)
    LOGGER.info(f"{len(done)} Tasks Finished")

    for task in done:
        if task.exception():
            await sub.nack(tasks[task])
            previous_failed[task] = tasks[task]
            LOGGER.error("Task failed:")
            LOGGER.error(_task_exception_str(task))
        else:
            await sub.ack(tasks[task])

    return (
        {t: tasks[t] for t in pending},
        previous_failed,
    )


async def _consume_and_reply(
    cmd: str,
    #
    in_queue: mq.Queue,
    out_queue: mq.Queue,
    #
    # for subprocess
    ftype_to_subproc: FileType,
    ftype_from_subproc: FileType,
    #
    timeout_wait_for_first_message: Optional[int],
    timeout_incoming: int,
    #
    file_writer: Callable[[Any, Path], None],
    file_reader: Callable[[Path], Any],
    #
    debug_dir: Path,
    keep_debug_dir: bool,
    #
    task_timeout: Optional[int],
    multitasking: int,
) -> int:
    """Consume and reply loop.

    Return number of processed tasks.
    """
    pending: AsyncioTaskMessages = {}
    failed: AsyncioTaskMessages = {}

    # for the first (set) of messages, use 'timeout_wait_for_first_message' if given
    in_queue.timeout = (
        timeout_wait_for_first_message
        if timeout_wait_for_first_message
        else timeout_incoming
    )

    # GO!
    total_msg_count = 0
    LOGGER.info(
        "Listening for messages from server to process tasks then send results..."
    )
    async with out_queue.open_pub() as pub:

        LOGGER.info(f"Processing up to {multitasking} tasks concurrently")
        async with in_queue.open_sub_manual_acking(multitasking) as sub:

            async for in_msg in sub.iter_messages():
                total_msg_count += 1
                LOGGER.info(f"Got a task to process (#{total_msg_count}): {in_msg}")

                if total_msg_count == 1:
                    utils.chirp_status("Tasking")

                task = asyncio.create_task(
                    process_msg_task(
                        in_msg.data,
                        cmd,
                        task_timeout,
                        ftype_to_subproc,
                        ftype_from_subproc,
                        file_writer,
                        file_reader,
                        debug_dir,
                        keep_debug_dir,
                        pub,
                    )
                )
                pending[task] = in_msg

                # if we've met max concurrent tasks, wait for the next one to finish
                while len(pending) >= multitasking:
                    LOGGER.info("Reached max task concurrency limit, waiting...")
                    pending, failed = await _ack_nack_finished_tasks(
                        sub,
                        pending,
                        return_when=asyncio.FIRST_COMPLETED,
                        previous_failed=failed,
                    )
                    # after the first set of messages, set the timeout to the "normal" amount
                    if in_queue.timeout != timeout_incoming:
                        in_queue.timeout = timeout_incoming

                # if 1+ fail, then don't consume anymore; wait for remaining tasks
                if failed:
                    LOGGER.info("1+ Tasks Failed: waiting for remaining tasks")
                    break

            LOGGER.info("No more new tasks to process")

            # wait for remaining tasks
            if pending:
                LOGGER.info("Waiting for remaining tasks to finish...")
                pending, failed = await _ack_nack_finished_tasks(
                    sub,
                    pending,
                    return_when=asyncio.ALL_COMPLETED,
                    previous_failed=failed,
                )
                if pending:
                    LOGGER.error(f"{len(pending)} tasks are pending after finish")

    # log/chirp
    chirp_msg = f"Done Tasking: completed {total_msg_count} task(s)"
    utils.chirp_status(chirp_msg)
    LOGGER.info(chirp_msg)
    # check if anything actually processed
    if not total_msg_count:
        LOGGER.warning("No Messages Were Received.")

    # cleanup
    if failed:
        raise RuntimeError(
            f"{len(failed)} Task(s) Failed: "
            f"{', '.join(_task_exception_str(f) for f in failed)}"
        )
    return total_msg_count


def main() -> None:
    """Start up EWMS Pilot subprocess to perform an MQ task."""

    parser = argparse.ArgumentParser(
        description="Start up EWMS Pilot subprocess to perform an MQ task",
        epilog="",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--cmd",  # alternatively we can go with a condor-like --executable and --arguments
        required=True,
        help="the command to give the subprocess script",
    )
    parser.add_argument(
        "--infile-type",
        type=FileType,
        help="the file type (extension) to use for files written for the pilot's subprocess",
    )
    parser.add_argument(
        "--outfile-type",
        type=FileType,
        help="the file type (exception) of the file to read from the pilot's subprocess",
    )
    parser.add_argument(
        "--multitasking",
        type=int,
        default=ENV.EWMS_PILOT_CONCURRENT_TASKS,
        help="the max number of tasks to process in parallel",
    )

    # mq args
    parser.add_argument(
        "--queue-incoming",
        required=True,
        help="the name of the incoming queue",
    )
    parser.add_argument(
        "--queue-outgoing",
        required=True,
        help="the name of the outgoing queue",
    )
    parser.add_argument(
        "--broker-client",
        default=ENV.EWMS_PILOT_BROKER_CLIENT,
        help="which kind of broker: pulsar, rabbitmq, etc.",
    )
    parser.add_argument(
        "-b",
        "--broker",
        default=ENV.EWMS_PILOT_BROKER_ADDRESS,
        help="The MQ broker URL to connect to",
    )
    parser.add_argument(
        "-a",
        "--auth-token",
        default=ENV.EWMS_PILOT_BROKER_AUTH_TOKEN,
        help="The MQ authentication token to use",
    )
    parser.add_argument(
        "--prefetch",
        default=_DEFAULT_PREFETCH,
        type=int,
        help="prefetch for incoming messages",
    )
    parser.add_argument(
        "--timeout-wait-for-first-message",
        default=None,
        type=int,
        help="timeout (seconds) for the first message to arrive at the pilot; "
        "defaults to `--timeout-incoming` value",
    )
    parser.add_argument(
        "--timeout-incoming",
        default=_DEFAULT_TIMEOUT_INCOMING,
        type=int,
        help="timeout (seconds) for messages TO pilot",
    )
    parser.add_argument(
        "--timeout-outgoing",
        default=_DEFAULT_TIMEOUT_OUTGOING,
        type=int,
        help="timeout (seconds) for messages FROM pilot",
    )
    parser.add_argument(
        "--task-timeout",
        default=ENV.EWMS_PILOT_TASK_TIMEOUT,
        type=int,
        help="timeout (seconds) for each task",
    )
    parser.add_argument(
        "--quarantine-time",
        default=ENV.EWMS_PILOT_QUARANTINE_TIME,
        type=int,
        help="amount of time to sleep after error (useful for preventing blackhole scenarios on condor)",
    )

    # logging args
    parser.add_argument(
        "-l",
        "--log",
        default=ENV.EWMS_PILOT_LOG,
        help="the output logging level (for first-party loggers)",
    )
    parser.add_argument(
        "--log-third-party",
        default=ENV.EWMS_PILOT_LOG_THIRD_PARTY,
        help="the output logging level for third-party loggers",
    )

    # testing/debugging args
    parser.add_argument(
        "--debug-directory",
        default="",
        type=argparse_tools.create_dir,
        help="a directory to write all the incoming/outgoing .pkl files "
        "(useful for debugging)",
    )

    args = parser.parse_args()
    logging_tools.set_level(
        args.log.upper(),
        first_party_loggers=[LOGGER],
        third_party_level=args.log_third_party,
        use_coloredlogs=True,
    )
    logging_tools.log_argparse_args(args, logger=LOGGER, level="WARNING")

    # GO!
    LOGGER.info(
        f"Starting up an EWMS Pilot for MQ task: {args.queue_incoming} -> {args.queue_outgoing}"
    )
    asyncio.run(
        consume_and_reply(
            cmd=args.cmd,
            broker_client=args.broker_client,
            ftype_to_subproc=args.infile_type,
            ftype_from_subproc=args.outfile_type,
            #
            broker_address=args.broker,
            auth_token=args.auth_token,
            queue_incoming=args.queue_incoming,
            queue_outgoing=args.queue_outgoing,
            prefetch=args.prefetch,
            timeout_wait_for_first_message=args.timeout_wait_for_first_message,
            timeout_incoming=args.timeout_incoming,
            timeout_outgoing=args.timeout_outgoing,
            # file_writer=UniversalFileInterface.write,
            # file_reader=UniversalFileInterface.read,
            debug_dir=args.debug_directory,
            task_timeout=args.task_timeout,
            quarantine_time=args.quarantine_time,
            multitasking=args.multitasking,
        )
    )
    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
