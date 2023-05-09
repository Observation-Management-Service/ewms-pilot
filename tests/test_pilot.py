"""Test pilot submodule."""

# pylint:disable=redefined-outer-name

import asyncio
import logging
import os
import re
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, List

import asyncstdlib as asl
import mqclient as mq
import pytest
from ewms_pilot import FileType, config, consume_and_reply

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("mqclient").setLevel(logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)


@pytest.fixture
def queue_incoming() -> str:
    """Get the name of a queue for talking to client(s)."""
    return mq.Queue.make_name()


@pytest.fixture
def queue_outgoing() -> str:
    """Get the name of a queue for talking "from" client(s)."""
    return mq.Queue.make_name()


@pytest.fixture
def debug_dir() -> Path:
    """Make a unique debug directory and return its Path."""
    dirpath = Path(f"./debug-dir/{time.time()}")
    dirpath.mkdir(parents=True)
    return dirpath


@pytest.fixture
def first_walk() -> list:
    """Get os.walk list for initial state."""
    return list(os.walk("."))


async def populate_queue(
    queue_incoming: str,
    msgs_to_subproc: list,
) -> None:
    """Send messages to queue."""
    to_client_q = mq.Queue(
        config.ENV.EWMS_PILOT_BROKER_CLIENT,
        address=config.ENV.EWMS_PILOT_BROKER_ADDRESS,
        name=queue_incoming,
    )

    async with to_client_q.open_pub() as pub:
        for i, msg in enumerate(msgs_to_subproc):
            await pub.send(msg)

    assert i + 1 == len(msgs_to_subproc)  # pylint:disable=undefined-loop-variable


async def assert_results(
    queue_outgoing: str,
    msgs_from_subproc: list,
) -> None:
    """Get messages and assert against expected results."""
    from_client_q = mq.Queue(
        config.ENV.EWMS_PILOT_BROKER_CLIENT,
        address=config.ENV.EWMS_PILOT_BROKER_ADDRESS,
        name=queue_outgoing,
    )
    received: list = []
    async with from_client_q.open_sub() as sub:
        async for i, msg in asl.enumerate(sub):
            print(f"{i}: {msg}")
            received.append(msg)

    assert len(received) == len(msgs_from_subproc)

    # check each entry (special handling for dict-types b/c not hashable)
    if msgs_from_subproc and isinstance(msgs_from_subproc[0], dict):
        assert set(str(r) for r in received) == set(str(m) for m in msgs_from_subproc)
    else:
        assert set(received) == set(msgs_from_subproc)


def assert_debug_dir(
    debug_dir: Path,
    ftype_to_subproc: FileType,
    n_tasks: int,
    files: List[str],
) -> List[Path]:
    all_files = []

    assert len(list(debug_dir.iterdir())) == n_tasks
    for path in debug_dir.iterdir():
        assert path.is_dir()

        task_id = path.name

        # look for in/out files
        for subpath in path.iterdir():
            assert subpath.is_file()
        these_files = list(files)  # copies
        if "in" in these_files:
            these_files.remove("in")
            these_files.append(f"in-{task_id}{ftype_to_subproc.value}")
        if "out" in these_files:
            these_files.remove("out")
            these_files.append(f"out-{task_id}{ftype_to_subproc.value}")
        assert sorted(p.name for p in path.iterdir()) == sorted(these_files)

        all_files.extend(list(path.iterdir()))
    return all_files


def assert_versus_first_walk(first_walk: list, persisted_files: List[Path]) -> None:
    """Check for persisted files."""
    expected_files = [
        os.path.join(root, fname)
        for root, _, filenames in first_walk
        for fname in filenames
    ]
    expected_files.extend(str(f.resolve()) for f in persisted_files)

    current_fpaths = [
        os.path.join(root, fname)
        for root, _, filenames in os.walk(".")
        for fname in filenames
    ]

    # use sets for better diffs in pytest logs
    assert set(current_fpaths) - set(expected_files) == set()  # any extra?
    assert set(expected_files) - set(current_fpaths) == set()  # any missing?


########################################################################################


async def test_000__txt(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: list,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    msgs_from_subproc = ["foofoo\n", "barbar\n", "bazbaz\n"]

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(queue_incoming, msgs_to_subproc),
        consume_and_reply(
            cmd="""python3 -c "
output = open('{{INFILE}}').read().strip() * 2;
print(output, file=open('{{OUTFILE}}','w'))" """,  # double cat
            # broker_client=,  # rely on env var
            # broker_address=,  # rely on env var
            # auth_token="",
            queue_incoming=queue_incoming,
            queue_outgoing=queue_outgoing,
            ftype_to_subproc=FileType.TXT,
            ftype_from_subproc=FileType.TXT,
            # file_writer=UniversalFileInterface.write, # see other tests
            # file_reader=UniversalFileInterface.read, # see other tests
            debug_dir=debug_dir,
        ),
    )

    await assert_results(queue_outgoing, msgs_from_subproc)
    debug_files = assert_debug_dir(
        debug_dir,
        FileType.TXT,
        len(msgs_from_subproc),
        ["in", "out", "stderrfile", "stdoutfile"],
    )
    assert_versus_first_walk(first_walk, debug_files)  # check for persisted files


async def test_001__txt__str_filetype(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: list,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    msgs_from_subproc = ["foofoo\n", "barbar\n", "bazbaz\n"]

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(queue_incoming, msgs_to_subproc),
        consume_and_reply(
            cmd="""python3 -c "
output = open('{{INFILE}}').read().strip() * 2;
print(output, file=open('{{OUTFILE}}','w'))" """,  # double cat
            # broker_client=,  # rely on env var
            # broker_address=,  # rely on env var
            # auth_token="",
            queue_incoming=queue_incoming,
            queue_outgoing=queue_outgoing,
            ftype_to_subproc=".txt",
            ftype_from_subproc=".txt",
            # file_writer=UniversalFileInterface.write, # see other tests
            # file_reader=UniversalFileInterface.read, # see other tests
            debug_dir=debug_dir,
        ),
    )

    await assert_results(queue_outgoing, msgs_from_subproc)
    debug_files = assert_debug_dir(
        debug_dir,
        FileType.TXT,
        len(msgs_from_subproc),
        ["in", "out", "stderrfile", "stdoutfile"],
    )
    assert_versus_first_walk(first_walk, debug_files)  # check for persisted files


async def test_100__json(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: list,
) -> None:
    """Test a normal .json-based pilot."""

    # some messages that would make sense json'ing
    msgs_to_subproc = [{"attr-0": v} for v in ["foo", "bar", "baz"]]
    msgs_from_subproc = [{"attr-a": v, "attr-b": v + v} for v in ["foo", "bar", "baz"]]

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(queue_incoming, msgs_to_subproc),
        consume_and_reply(
            cmd="""python3 -c "
import json;
input=json.load(open('{{INFILE}}'));
v=input['attr-0'];
output={'attr-a':v, 'attr-b':v+v};
json.dump(output, open('{{OUTFILE}}','w'))" """,
            # broker_client=,  # rely on env var
            # broker_address=,  # rely on env var
            # auth_token="",
            queue_incoming=queue_incoming,
            queue_outgoing=queue_outgoing,
            ftype_to_subproc=FileType.JSON,
            ftype_from_subproc=FileType.JSON,
            # file_writer=UniversalFileInterface.write, # see other tests
            # file_reader=UniversalFileInterface.read, # see other tests
            debug_dir=debug_dir,
        ),
    )

    await assert_results(queue_outgoing, msgs_from_subproc)
    debug_files = assert_debug_dir(
        debug_dir,
        FileType.JSON,
        len(msgs_from_subproc),
        ["in", "out", "stderrfile", "stdoutfile"],
    )
    assert_versus_first_walk(first_walk, debug_files)  # check for persisted files


async def test_200__pickle(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: list,
) -> None:
    """Test a normal .pkl-based pilot."""

    # some messages that would make sense pickling
    msgs_to_subproc = [date(1995, 12, 3), date(2022, 9, 29), date(2063, 4, 5)]
    msgs_from_subproc = [d + timedelta(days=1) for d in msgs_to_subproc]

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(queue_incoming, msgs_to_subproc),
        consume_and_reply(
            cmd="""python3 -c "
import pickle;
from datetime import date, timedelta;
input=pickle.load(open('{{INFILE}}','rb'));
output=input+timedelta(days=1);
pickle.dump(output, open('{{OUTFILE}}','wb'))" """,
            # broker_client=,  # rely on env var
            # broker_address=,  # rely on env var
            # auth_token="",
            queue_incoming=queue_incoming,
            queue_outgoing=queue_outgoing,
            ftype_to_subproc=FileType.PKL,
            ftype_from_subproc=FileType.PKL,
            # file_writer=UniversalFileInterface.write, # see other tests
            # file_reader=UniversalFileInterface.read, # see other tests
            debug_dir=debug_dir,
        ),
    )

    await assert_results(queue_outgoing, msgs_from_subproc)
    debug_files = assert_debug_dir(
        debug_dir,
        FileType.PKL,
        len(msgs_from_subproc),
        ["in", "out", "stderrfile", "stdoutfile"],
    )
    assert_versus_first_walk(first_walk, debug_files)  # check for persisted files


async def test_300__writer_reader(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: list,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    msgs_from_subproc = ["output: oofoof\n", "output: rabrab\n", "output: zabzab\n"]

    def reverse_writer(text: Any, fpath: Path) -> None:
        with open(fpath, "w") as f:
            f.write(text[::-1])

    def reader_w_prefix(fpath: Path) -> str:
        with open(fpath) as f:
            return f"output: {f.read()}"

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(queue_incoming, msgs_to_subproc),
        consume_and_reply(
            cmd="""python3 -c "
output = open('{{INFILE}}').read().strip() * 2;
print(output, file=open('{{OUTFILE}}','w'))" """,  # double cat
            # broker_client=,  # rely on env var
            # broker_address=,  # rely on env var
            # auth_token="",
            queue_incoming=queue_incoming,
            queue_outgoing=queue_outgoing,
            ftype_to_subproc=FileType.TXT,
            ftype_from_subproc=FileType.TXT,
            file_writer=reverse_writer,
            file_reader=reader_w_prefix,
            debug_dir=debug_dir,
        ),
    )

    await assert_results(queue_outgoing, msgs_from_subproc)
    debug_files = assert_debug_dir(
        debug_dir,
        FileType.TXT,
        len(msgs_from_subproc),
        ["in", "out", "stderrfile", "stdoutfile"],
    )
    assert_versus_first_walk(first_walk, debug_files)  # check for persisted files


async def test_400__exception(
    queue_incoming: str,
    queue_outgoing: str,
    # debug_dir: Path,
    first_walk: list,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    # msgs_from_subproc = ["foofoo\n", "barbar\n", "bazbaz\n"]

    start_time = time.time()

    # run producer & consumer concurrently
    with pytest.raises(
        RuntimeError,
        match=r"1 Task\(s\) Failed: "
        r"\[TaskSubprocessError: Subprocess completed with exit code 1: ValueError: no good!\]",
    ):
        await asyncio.gather(
            populate_queue(queue_incoming, msgs_to_subproc),
            consume_and_reply(
                cmd="""python3 -c "raise ValueError('no good!')" """,
                # broker_client=,  # rely on env var
                # broker_address=,  # rely on env var
                # auth_token="",
                queue_incoming=queue_incoming,
                queue_outgoing=queue_outgoing,
                ftype_to_subproc=FileType.TXT,
                ftype_from_subproc=FileType.TXT,
                # file_writer=UniversalFileInterface.write, # see other tests
                # file_reader=UniversalFileInterface.read, # see other tests
                # debug_dir=debug_dir,
            ),
        )

    assert time.time() - start_time <= 2  # no quarantine time

    await assert_results(queue_outgoing, [])
    # debug_files = assert_debug_dir(
    #     debug_dir,
    #     FileType.TXT,
    #     [],
    #     ["in", "out", "stderrfile", "stdoutfile"],
    # )
    assert_versus_first_walk(first_walk, [])  # check for persisted files


async def test_401__exception_with_outwriting(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: list,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    # msgs_from_subproc = ["foofoo\n", "barbar\n", "bazbaz\n"]

    start_time = time.time()

    # run producer & consumer concurrently
    with pytest.raises(
        RuntimeError,
        match=r"1 Task\(s\) Failed: "
        r"\[TaskSubprocessError: Subprocess completed with exit code 1: ValueError: no good!\]",
    ):
        await asyncio.gather(
            populate_queue(queue_incoming, msgs_to_subproc),
            consume_and_reply(
                cmd="""python3 -c "
output = open('{{INFILE}}').read().strip() * 2;
print(output, file=open('{{OUTFILE}}','w'))
raise ValueError('no good!')" """,  # double cat
                # broker_client=,  # rely on env var
                # broker_address=,  # rely on env var
                # auth_token="",
                queue_incoming=queue_incoming,
                queue_outgoing=queue_outgoing,
                ftype_to_subproc=FileType.TXT,
                ftype_from_subproc=FileType.TXT,
                # file_writer=UniversalFileInterface.write, # see other tests
                # file_reader=UniversalFileInterface.read, # see other tests
                debug_dir=debug_dir,
            ),
        )

    assert time.time() - start_time <= 2  # no quarantine time

    await assert_results(queue_outgoing, [])
    debug_files = assert_debug_dir(
        debug_dir,
        FileType.TXT,
        1,  # only 1 message was processed before error
        ["in", "out", "stderrfile", "stdoutfile"],
    )
    assert_versus_first_walk(first_walk, debug_files)  # check for persisted files


async def test_410__blackhole_quarantine(
    queue_incoming: str,
    queue_outgoing: str,
    # debug_dir: Path,
    first_walk: list,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    # msgs_from_subproc = ["foofoo\n", "barbar\n", "bazbaz\n"]

    start_time = time.time()

    # run producer & consumer concurrently
    with pytest.raises(
        RuntimeError,
        match=r"1 Task\(s\) Failed: "
        r"\[TaskSubprocessError: Subprocess completed with exit code 1: ValueError: no good!\]",
    ):
        await asyncio.gather(
            populate_queue(queue_incoming, msgs_to_subproc),
            consume_and_reply(
                cmd="""python3 -c "raise ValueError('no good!')" """,
                # broker_client=,  # rely on env var
                # broker_address=,  # rely on env var
                # auth_token="",
                queue_incoming=queue_incoming,
                queue_outgoing=queue_outgoing,
                ftype_to_subproc=FileType.TXT,
                ftype_from_subproc=FileType.TXT,
                # file_writer=UniversalFileInterface.write, # see other tests
                # file_reader=UniversalFileInterface.read, # see other tests
                # debug_dir=debug_dir,
                quarantine_time=20,
            ),
        )

    assert time.time() - start_time >= 20  # did quarantine_time work?

    await assert_results(queue_outgoing, [])
    # debug_files = assert_debug_dir(
    #     debug_dir,
    #     FileType.TXT,
    #     [],
    #     ["in", "out", "stderrfile", "stdoutfile"],
    # )
    assert_versus_first_walk(first_walk, [])  # check for persisted files


async def test_420__timeout(
    queue_incoming: str,
    queue_outgoing: str,
    # debug_dir: Path,
    first_walk: list,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    # msgs_from_subproc = ["foofoo\n", "barbar\n", "bazbaz\n"]

    start_time = time.time()

    # run producer & consumer concurrently
    with pytest.raises(
        RuntimeError, match=re.escape("1 Task(s) Failed: [TimeoutError: ]")
    ):
        await asyncio.gather(
            populate_queue(queue_incoming, msgs_to_subproc),
            consume_and_reply(
                cmd="""python3 -c "import time; time.sleep(30)" """,
                # broker_client=,  # rely on env var
                # broker_address=,  # rely on env var
                # auth_token="",
                queue_incoming=queue_incoming,
                queue_outgoing=queue_outgoing,
                ftype_to_subproc=FileType.TXT,
                ftype_from_subproc=FileType.TXT,
                # file_writer=UniversalFileInterface.write, # see other tests
                # file_reader=UniversalFileInterface.read, # see other tests
                # debug_dir=debug_dir,
                task_timeout=2,
            ),
        )

    assert time.time() - start_time <= 5  # no quarantine time

    await assert_results(queue_outgoing, [])
    # debug_files = assert_debug_dir(
    #     debug_dir,
    #     FileType.TXT,
    #     [],
    #     ["in", "out", "stderrfile", "stdoutfile"],
    # )
    assert_versus_first_walk(first_walk, [])  # check for persisted files


async def test_500__multitasking(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: list,
) -> None:
    """Test multitasking within the pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    msgs_from_subproc = ["foofoo\n", "barbar\n", "bazbaz\n"]

    multitasking = 4
    start_time = time.time()

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(queue_incoming, msgs_to_subproc),
        consume_and_reply(
            cmd="""python3 -c "
import time
output = open('{{INFILE}}').read().strip() * 2;
time.sleep(5)
print(output, file=open('{{OUTFILE}}','w'))" """,  # double cat
            # broker_client=,  # rely on env var
            # broker_address=,  # rely on env var
            # auth_token="",
            queue_incoming=queue_incoming,
            queue_outgoing=queue_outgoing,
            ftype_to_subproc=FileType.TXT,
            ftype_from_subproc=FileType.TXT,
            # file_writer=UniversalFileInterface.write, # see other tests
            # file_reader=UniversalFileInterface.read, # see other tests
            debug_dir=debug_dir,
            multitasking=multitasking,
        ),
    )

    # it should've take ~5 seconds to complete all tasks
    print(time.time() - start_time)
    assert time.time() - start_time < multitasking * len(msgs_to_subproc)

    await assert_results(queue_outgoing, msgs_from_subproc)
    debug_files = assert_debug_dir(
        debug_dir,
        FileType.TXT,
        len(msgs_from_subproc),
        ["in", "out", "stderrfile", "stdoutfile"],
    )
    assert_versus_first_walk(first_walk, debug_files)  # check for persisted files


async def test_510__multitasking_exceptions(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: list,
) -> None:
    """Test multitasking within the pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    msgs_from_subproc = ["foofoo\n", "barbar\n", "bazbaz\n"]

    multitasking = 4
    start_time = time.time()

    # run producer & consumer concurrently
    with pytest.raises(
        RuntimeError,
        match=r"3 Task\(s\) Failed: "
        r"\[TaskSubprocessError: Subprocess completed with exit code 1: ValueError: gotta fail: (foofoo|barbar|bazbaz)\], "
        r"\[TaskSubprocessError: Subprocess completed with exit code 1: ValueError: gotta fail: (foofoo|barbar|bazbaz)\], "
        r"\[TaskSubprocessError: Subprocess completed with exit code 1: ValueError: gotta fail: (foofoo|barbar|bazbaz)\]",
    ) as e:
        await asyncio.gather(
            populate_queue(queue_incoming, msgs_to_subproc),
            consume_and_reply(
                cmd="""python3 -c "
import time
output = open('{{INFILE}}').read().strip() * 2;
time.sleep(5)
print(output, file=open('{{OUTFILE}}','w'))
raise ValueError('gotta fail: ' + output.strip())" """,  # double cat
                # broker_client=,  # rely on env var
                # broker_address=,  # rely on env var
                # auth_token="",
                queue_incoming=queue_incoming,
                queue_outgoing=queue_outgoing,
                ftype_to_subproc=FileType.TXT,
                ftype_from_subproc=FileType.TXT,
                # file_writer=UniversalFileInterface.write, # see other tests
                # file_reader=UniversalFileInterface.read, # see other tests
                debug_dir=debug_dir,
                multitasking=multitasking,
            ),
        )
    # check each exception only occurred n-times -- much easier this way than regex (lots of permutations)
    assert str(e.value).count("ValueError: gotta fail: foofoo") == 1
    assert str(e.value).count("ValueError: gotta fail: barbar") == 1
    assert str(e.value).count("ValueError: gotta fail: bazbaz") == 1

    # it should've take ~5 seconds to complete all tasks
    print(time.time() - start_time)
    assert time.time() - start_time < multitasking * len(msgs_to_subproc)

    await assert_results(queue_outgoing, [])
    debug_files = assert_debug_dir(
        debug_dir,
        FileType.TXT,
        len(msgs_from_subproc),
        ["in", "out", "stderrfile", "stdoutfile"],
    )
    assert_versus_first_walk(first_walk, debug_files)  # check for persisted files
