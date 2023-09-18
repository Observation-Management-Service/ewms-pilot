"""Test pilot submodule."""

# pylint:disable=redefined-outer-name

import asyncio
import logging
import os
import re
import time
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any, List, Optional, Tuple
from unittest.mock import patch

import asyncstdlib as asl
import mqclient as mq
import pytest
from ewms_pilot import FileType, config, consume_and_reply
from ewms_pilot.config import ENV

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger("mqclient").setLevel(logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)


TIMEOUT_INCOMING = 3

MSGS_TO_SUBPROC = ["item" + str(i) for i in range(30)]


@pytest.fixture
def queue_incoming() -> str:
    """Get the name of a queue for talking to client(s)."""
    return mq.Queue.make_name()


@pytest.fixture
def unique_pwd() -> None:
    """Create unique directory and cd to it.

    Enables tests to be ran in parallel without file conflicts.
    """
    root = Path(uuid.uuid4().hex)
    root.mkdir()
    os.chdir(root)


@pytest.fixture
def queue_outgoing() -> str:
    """Get the name of a queue for talking "from" client(s)."""
    return mq.Queue.make_name()


@pytest.fixture
def debug_dir() -> Path:
    """Return a unique debug directory Path.

    Don't create since it'll be created by the pilot.
    """
    return Path(f"./debug-dir-{time.time()}")


OSWalkList = List[Tuple[str, List[str], List[str]]]


@pytest.fixture
def first_walk() -> OSWalkList:
    """Get os.walk list for initial state."""
    return list(os.walk("."))


async def populate_queue(
    queue_incoming: str,
    msgs_to_subproc: list,
    timeout_incoming: int,
) -> None:
    """Send messages to queue."""
    to_client_q = mq.Queue(
        config.ENV.EWMS_PILOT_BROKER_CLIENT,
        address=config.ENV.EWMS_PILOT_BROKER_ADDRESS,
        name=queue_incoming,
    )

    async with to_client_q.open_pub() as pub:
        for i, msg in enumerate(msgs_to_subproc):
            if i and i % 2 == 0:  # add some chaos -- make the queue not saturated
                await asyncio.sleep(timeout_incoming / 2)
            await pub.send(msg)

    assert i + 1 == len(msgs_to_subproc)  # pylint:disable=undefined-loop-variable


async def assert_results(
    queue_outgoing: str,
    msgs_expected: list,
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

    assert len(received) == len(msgs_expected)

    # check each entry (special handling for dict-types b/c not hashable)
    if msgs_expected and isinstance(msgs_expected[0], dict):
        assert set(str(r) for r in received) == set(str(m) for m in msgs_expected)
    else:
        assert set(received) == set(msgs_expected)


def assert_debug_dir(
    debug_dir: Path,
    ftype_to_subproc: FileType,
    n_tasks: int,
    files: List[str],
) -> None:
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


def os_walk_to_flat_abspaths(os_walk: OSWalkList) -> List[str]:
    filepaths = [
        os.path.abspath(os.path.join(root, fname))
        for root, _, filenames in os_walk
        for fname in filenames
    ]
    dirpaths = [
        os.path.abspath(os.path.join(root, dname))
        for root, dirnames, _ in os_walk
        for dname in dirnames
    ]
    rootpaths = [os.path.abspath(root) for root, _, _ in os_walk]
    return sorted(set(filepaths + dirpaths + rootpaths))


def assert_versus_os_walk(first_walk: OSWalkList, persisted_dirs: List[Path]) -> None:
    """Check for persisted files."""
    expected_files = os_walk_to_flat_abspaths(first_walk)
    for dpath in persisted_dirs:  # add all files nested under each dir
        expected_files.extend(os_walk_to_flat_abspaths(list(os.walk(dpath))))

    current_fpaths = os_walk_to_flat_abspaths(list(os.walk(".")))

    # use sets for better diffs in pytest logs
    assert set(current_fpaths) == set(expected_files)


########################################################################################


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
async def test_000__txt(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = MSGS_TO_SUBPROC
    msgs_outgoing_expected = [f"{x}{x}\n" for x in MSGS_TO_SUBPROC]

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(
            queue_incoming,
            msgs_to_subproc,
            timeout_incoming=TIMEOUT_INCOMING,
        ),
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
            timeout_incoming=TIMEOUT_INCOMING,
            # file_writer=UniversalFileInterface.write, # see other tests
            # file_reader=UniversalFileInterface.read, # see other tests
            debug_dir=debug_dir if use_debug_dir else None,
        ),
    )

    await assert_results(queue_outgoing, msgs_outgoing_expected)
    if use_debug_dir:
        assert_debug_dir(
            debug_dir,
            FileType.TXT,
            len(msgs_outgoing_expected),
            ["in", "out", "stderrfile", "stdoutfile"],
        )
    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
async def test_001__txt__str_filetype(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = MSGS_TO_SUBPROC
    msgs_outgoing_expected = [f"{x}{x}\n" for x in MSGS_TO_SUBPROC]

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(
            queue_incoming,
            msgs_to_subproc,
            timeout_incoming=TIMEOUT_INCOMING,
        ),
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
            timeout_incoming=TIMEOUT_INCOMING,
            # file_writer=UniversalFileInterface.write, # see other tests
            # file_reader=UniversalFileInterface.read, # see other tests
            debug_dir=debug_dir if use_debug_dir else None,
        ),
    )

    await assert_results(queue_outgoing, msgs_outgoing_expected)
    if use_debug_dir:
        assert_debug_dir(
            debug_dir,
            FileType.TXT,
            len(msgs_outgoing_expected),
            ["in", "out", "stderrfile", "stdoutfile"],
        )
    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
async def test_100__json(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
) -> None:
    """Test a normal .json-based pilot."""

    # some messages that would make sense json'ing
    msgs_to_subproc = [{"attr-0": v} for v in MSGS_TO_SUBPROC]
    msgs_outgoing_expected = [{"attr-a": v, "attr-b": v + v} for v in MSGS_TO_SUBPROC]

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(
            queue_incoming,
            msgs_to_subproc,
            timeout_incoming=TIMEOUT_INCOMING,
        ),
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
            timeout_incoming=TIMEOUT_INCOMING,
            # file_writer=UniversalFileInterface.write, # see other tests
            # file_reader=UniversalFileInterface.read, # see other tests
            debug_dir=debug_dir if use_debug_dir else None,
        ),
    )

    await assert_results(queue_outgoing, msgs_outgoing_expected)
    if use_debug_dir:
        assert_debug_dir(
            debug_dir,
            FileType.JSON,
            len(msgs_outgoing_expected),
            ["in", "out", "stderrfile", "stdoutfile"],
        )
    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
async def test_200__pickle(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
) -> None:
    """Test a normal .pkl-based pilot."""

    # some messages that would make sense pickling
    msgs_to_subproc = [
        date(
            1995 + int(re.sub(r"[^0-9]", "", x)),
            int(re.sub(r"[^0-9]", "", x)) % 12 + 1,
            int(re.sub(r"[^0-9]", "", x)) % 28 + 1,
        )
        for x in MSGS_TO_SUBPROC
    ]
    msgs_outgoing_expected = [d + timedelta(days=1) for d in msgs_to_subproc]

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(
            queue_incoming,
            msgs_to_subproc,
            timeout_incoming=TIMEOUT_INCOMING,
        ),
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
            timeout_incoming=TIMEOUT_INCOMING,
            # file_writer=UniversalFileInterface.write, # see other tests
            # file_reader=UniversalFileInterface.read, # see other tests
            debug_dir=debug_dir if use_debug_dir else None,
        ),
    )

    await assert_results(queue_outgoing, msgs_outgoing_expected)
    if use_debug_dir:
        assert_debug_dir(
            debug_dir,
            FileType.PKL,
            len(msgs_outgoing_expected),
            ["in", "out", "stderrfile", "stdoutfile"],
        )
    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
async def test_300__writer_reader(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = MSGS_TO_SUBPROC
    msgs_outgoing_expected = [f"output: {x[::-1]}{x[::-1]}\n" for x in MSGS_TO_SUBPROC]

    def reverse_writer(text: Any, fpath: Path) -> None:
        with open(fpath, "w") as f:
            f.write(text[::-1])

    def reader_w_prefix(fpath: Path) -> str:
        with open(fpath) as f:
            return f"output: {f.read()}"

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(
            queue_incoming,
            msgs_to_subproc,
            timeout_incoming=TIMEOUT_INCOMING,
        ),
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
            timeout_incoming=TIMEOUT_INCOMING,
            file_writer=reverse_writer,
            file_reader=reader_w_prefix,
            debug_dir=debug_dir if use_debug_dir else None,
        ),
    )

    await assert_results(queue_outgoing, msgs_outgoing_expected)
    if use_debug_dir:
        assert_debug_dir(
            debug_dir,
            FileType.TXT,
            len(msgs_outgoing_expected),
            ["in", "out", "stderrfile", "stdoutfile"],
        )
    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
@pytest.mark.parametrize("quarantine", [None, 20])
async def test_400__exception(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
    quarantine: Optional[int],
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = MSGS_TO_SUBPROC
    # msgs_outgoing_expected = [f"{x}{x}\n" for x in MSGS_TO_SUBPROC]

    start_time = time.time()

    # run producer & consumer concurrently
    with pytest.raises(
        RuntimeError,
        match=r"1 TASK\(S\) FAILED: "
        r"TaskSubprocessError\('Subprocess completed with exit code 1: ValueError: no good!'\)",
    ):
        await asyncio.gather(
            populate_queue(
                queue_incoming,
                msgs_to_subproc,
                timeout_incoming=TIMEOUT_INCOMING,
            ),
            consume_and_reply(
                cmd="""python3 -c "raise ValueError('no good!')" """,
                # broker_client=,  # rely on env var
                # broker_address=,  # rely on env var
                # auth_token="",
                queue_incoming=queue_incoming,
                queue_outgoing=queue_outgoing,
                ftype_to_subproc=FileType.TXT,
                ftype_from_subproc=FileType.TXT,
                timeout_incoming=TIMEOUT_INCOMING,
                # file_writer=UniversalFileInterface.write, # see other tests
                # file_reader=UniversalFileInterface.read, # see other tests
                debug_dir=debug_dir if use_debug_dir else None,
                quarantine_time=quarantine if quarantine else 0,
            ),
        )

    if quarantine:
        assert time.time() - start_time >= quarantine  # did quarantine_time work?
    else:
        assert time.time() - start_time <= 3  # no quarantine time

    await assert_results(queue_outgoing, [])
    if use_debug_dir:
        assert_debug_dir(
            debug_dir,
            FileType.TXT,
            1,  # only 1 message was processed before error
            ["in", "stderrfile", "stdoutfile"],
        )
    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
async def test_420__timeout(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = MSGS_TO_SUBPROC
    # msgs_outgoing_expected = [f"{x}{x}\n" for x in MSGS_TO_SUBPROC]

    start_time = time.time()

    # run producer & consumer concurrently
    with pytest.raises(
        RuntimeError, match=re.escape("1 TASK(S) FAILED: TimeoutError()")
    ):
        await asyncio.gather(
            populate_queue(
                queue_incoming,
                msgs_to_subproc,
                timeout_incoming=TIMEOUT_INCOMING,
            ),
            consume_and_reply(
                cmd="""python3 -c "import time; time.sleep(30)" """,
                # broker_client=,  # rely on env var
                # broker_address=,  # rely on env var
                # auth_token="",
                queue_incoming=queue_incoming,
                queue_outgoing=queue_outgoing,
                ftype_to_subproc=FileType.TXT,
                ftype_from_subproc=FileType.TXT,
                timeout_incoming=TIMEOUT_INCOMING,
                # file_writer=UniversalFileInterface.write, # see other tests
                # file_reader=UniversalFileInterface.read, # see other tests
                debug_dir=debug_dir if use_debug_dir else None,
                task_timeout=2,
            ),
        )

    assert time.time() - start_time <= 5  # no quarantine time

    await assert_results(queue_outgoing, [])
    if use_debug_dir:
        assert_debug_dir(
            debug_dir,
            FileType.TXT,
            1,
            ["in", "stderrfile", "stdoutfile"],
        )
    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )


MULTITASKING = 4
PREFETCH_TEST_PARAMETERS = sorted(
    set(
        [
            ENV.EWMS_PILOT_PREFETCH,
            1,
            2,
            MULTITASKING - 1,
            MULTITASKING,
            MULTITASKING + 1,
            77,
        ]
    )
)


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
@pytest.mark.parametrize("prefetch", PREFETCH_TEST_PARAMETERS)
async def test_500__concurrent_load_multitasking(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
    prefetch: int,
) -> None:
    """Test multitasking within the pilot."""
    msgs_to_subproc = MSGS_TO_SUBPROC
    msgs_outgoing_expected = [f"{x}{x}\n" for x in MSGS_TO_SUBPROC]

    start_time = time.time()

    # run producer & consumer concurrently
    await asyncio.gather(
        populate_queue(
            queue_incoming,
            msgs_to_subproc,
            timeout_incoming=TIMEOUT_INCOMING,
        ),
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
            timeout_incoming=TIMEOUT_INCOMING,
            prefetch=prefetch,
            # file_writer=UniversalFileInterface.write, # see other tests
            # file_reader=UniversalFileInterface.read, # see other tests
            debug_dir=debug_dir if use_debug_dir else None,
            multitasking=MULTITASKING,
        ),
    )

    # it should've taken ~5 seconds to complete all tasks (but we're on 1 cpu so it takes longer)
    print(time.time() - start_time)

    await assert_results(queue_outgoing, msgs_outgoing_expected)
    if use_debug_dir:
        assert_debug_dir(
            debug_dir,
            FileType.TXT,
            len(msgs_outgoing_expected),
            ["in", "out", "stderrfile", "stdoutfile"],
        )
    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
@pytest.mark.parametrize("prefetch", PREFETCH_TEST_PARAMETERS)
async def test_510__concurrent_load_multitasking_exceptions(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
    prefetch: int,
) -> None:
    """Test multitasking within the pilot."""
    msgs_to_subproc = MSGS_TO_SUBPROC
    msgs_outgoing_expected = [f"{x}{x}\n" for x in MSGS_TO_SUBPROC]

    start_time = time.time()

    # run producer & consumer concurrently
    with pytest.raises(
        RuntimeError,
        match=r"3 TASK\(S\) FAILED: "
        r"TaskSubprocessError\('Subprocess completed with exit code 1: ValueError: gotta fail: (foofoo|barbar|bazbaz)'\), "
        r"TaskSubprocessError\('Subprocess completed with exit code 1: ValueError: gotta fail: (foofoo|barbar|bazbaz)'\), "
        r"TaskSubprocessError\('Subprocess completed with exit code 1: ValueError: gotta fail: (foofoo|barbar|bazbaz)'\)",
    ) as e:
        await asyncio.gather(
            populate_queue(
                queue_incoming,
                msgs_to_subproc,
                timeout_incoming=TIMEOUT_INCOMING,
            ),
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
                timeout_incoming=TIMEOUT_INCOMING,
                prefetch=prefetch,
                # file_writer=UniversalFileInterface.write, # see other tests
                # file_reader=UniversalFileInterface.read, # see other tests
                debug_dir=debug_dir if use_debug_dir else None,
                multitasking=MULTITASKING,
            ),
        )
    # check each exception only occurred n-times -- much easier this way than regex (lots of permutations)
    assert str(e.value).count("ValueError: gotta fail: foofoo") == 1
    assert str(e.value).count("ValueError: gotta fail: barbar") == 1
    assert str(e.value).count("ValueError: gotta fail: bazbaz") == 1

    # it should've taken ~5 seconds to complete all tasks (but we're on 1 cpu so it takes longer)
    print(time.time() - start_time)

    await assert_results(queue_outgoing, [])
    if use_debug_dir:
        assert_debug_dir(
            debug_dir,
            FileType.TXT,
            len(msgs_outgoing_expected),
            ["in", "out", "stderrfile", "stdoutfile"],
        )
    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
@pytest.mark.parametrize("prefetch", PREFETCH_TEST_PARAMETERS)
async def test_520__preload_multitasking(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
    prefetch: int,
) -> None:
    """Test multitasking within the pilot."""
    msgs_to_subproc = MSGS_TO_SUBPROC
    msgs_outgoing_expected = [f"{x}{x}\n" for x in MSGS_TO_SUBPROC]

    start_time = time.time()

    await populate_queue(
        queue_incoming,
        msgs_to_subproc,
        timeout_incoming=TIMEOUT_INCOMING,
    )

    await consume_and_reply(
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
        timeout_incoming=TIMEOUT_INCOMING,
        prefetch=prefetch,
        # file_writer=UniversalFileInterface.write, # see other tests
        # file_reader=UniversalFileInterface.read, # see other tests
        debug_dir=debug_dir if use_debug_dir else None,
        multitasking=MULTITASKING,
    )

    # it should've taken ~5 seconds to complete all tasks (but we're on 1 cpu so it takes longer)
    print(time.time() - start_time)

    await assert_results(queue_outgoing, msgs_outgoing_expected)
    if use_debug_dir:
        assert_debug_dir(
            debug_dir,
            FileType.TXT,
            len(msgs_outgoing_expected),
            ["in", "out", "stderrfile", "stdoutfile"],
        )
    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
@pytest.mark.parametrize("prefetch", PREFETCH_TEST_PARAMETERS)
async def test_530__preload_multitasking_exceptions(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
    prefetch: int,
) -> None:
    """Test multitasking within the pilot."""
    msgs_to_subproc = MSGS_TO_SUBPROC
    msgs_outgoing_expected = [f"{x}{x}\n" for x in MSGS_TO_SUBPROC]

    start_time = time.time()

    await populate_queue(
        queue_incoming,
        msgs_to_subproc,
        timeout_incoming=TIMEOUT_INCOMING,
    )

    with pytest.raises(
        RuntimeError,
        match=r"3 TASK\(S\) FAILED: "
        r"TaskSubprocessError\('Subprocess completed with exit code 1: ValueError: gotta fail: (foofoo|barbar|bazbaz)'\), "
        r"TaskSubprocessError\('Subprocess completed with exit code 1: ValueError: gotta fail: (foofoo|barbar|bazbaz)'\), "
        r"TaskSubprocessError\('Subprocess completed with exit code 1: ValueError: gotta fail: (foofoo|barbar|bazbaz)'\)",
    ) as e:
        await consume_and_reply(
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
            timeout_incoming=TIMEOUT_INCOMING,
            prefetch=prefetch,
            # file_writer=UniversalFileInterface.write, # see other tests
            # file_reader=UniversalFileInterface.read, # see other tests
            debug_dir=debug_dir if use_debug_dir else None,
            multitasking=MULTITASKING,
        )
    # check each exception only occurred n-times -- much easier this way than regex (lots of permutations)
    assert str(e.value).count("ValueError: gotta fail: foofoo") == 1
    assert str(e.value).count("ValueError: gotta fail: barbar") == 1
    assert str(e.value).count("ValueError: gotta fail: bazbaz") == 1

    # it should've taken ~5 seconds to complete all tasks (but we're on 1 cpu so it takes longer)
    print(time.time() - start_time)

    await assert_results(queue_outgoing, [])
    if use_debug_dir:
        assert_debug_dir(
            debug_dir,
            FileType.TXT,
            len(msgs_outgoing_expected),
            ["in", "out", "stderrfile", "stdoutfile"],
        )
    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )


TEST_1000_SLEEP = 150.0  # anything lower doesn't upset rabbitmq enough


@pytest.mark.usefixtures("unique_pwd")
@pytest.mark.parametrize("use_debug_dir", [True, False])
@pytest.mark.parametrize(
    "refresh_interval_rabbitmq_heartbeat_interval",
    [
        TEST_1000_SLEEP * 10,
        TEST_1000_SLEEP,
        TEST_1000_SLEEP / 10,
    ],
)
async def test_1000__rabbitmq_heartbeat_workaround(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
    first_walk: OSWalkList,
    use_debug_dir: bool,
    refresh_interval_rabbitmq_heartbeat_interval: float,
) -> None:
    """Test a normal .txt-based pilot."""
    if config.ENV.EWMS_PILOT_BROKER_CLIENT != "rabbitmq":
        return

    msgs_to_subproc = MSGS_TO_SUBPROC
    msgs_outgoing_expected = [f"{x}{x}\n" for x in MSGS_TO_SUBPROC]

    timeout_incoming = int(refresh_interval_rabbitmq_heartbeat_interval * 1.5)

    async def _test() -> None:
        await asyncio.gather(
            populate_queue(
                queue_incoming,
                msgs_to_subproc,
                timeout_incoming=timeout_incoming,
            ),
            consume_and_reply(
                cmd="""python3 -c "
import time;
output = open('{{INFILE}}').read().strip() * 2;
time.sleep("""
                + str(TEST_1000_SLEEP)
                + """);
print(output, file=open('{{OUTFILE}}','w'))" """,  # double cat
                # broker_client=,  # rely on env var
                # broker_address=,  # rely on env var
                # auth_token="",
                queue_incoming=queue_incoming,
                queue_outgoing=queue_outgoing,
                ftype_to_subproc=FileType.TXT,
                ftype_from_subproc=FileType.TXT,
                timeout_incoming=timeout_incoming,
                # file_writer=UniversalFileInterface.write, # see other tests
                # file_reader=UniversalFileInterface.read, # see other tests
                debug_dir=debug_dir if use_debug_dir else None,
            ),
        )

    # run producer & consumer concurrently
    with patch(
        "ewms_pilot.pilot._REFRESH_INTERVAL",
        refresh_interval_rabbitmq_heartbeat_interval,
    ), patch(
        "ewms_pilot.pilot.Housekeeping.RABBITMQ_HEARTBEAT_INTERVAL",
        refresh_interval_rabbitmq_heartbeat_interval,
    ):
        if refresh_interval_rabbitmq_heartbeat_interval > TEST_1000_SLEEP:
            with pytest.raises(
                RuntimeError,
                match=re.escape(
                    "1 TASK(S) FAILED: MQClientException('pika.exceptions.StreamLostError: may be due to a missed heartbeat')"
                ),
            ):
                await _test()
                await assert_results(queue_outgoing, [])
                if use_debug_dir:
                    assert_debug_dir(
                        debug_dir,
                        FileType.TXT,
                        len([]),
                        ["in", "out", "stderrfile", "stdoutfile"],
                    )
        elif refresh_interval_rabbitmq_heartbeat_interval == TEST_1000_SLEEP:
            with pytest.raises(mq.broker_client_interface.ClosingFailedException):
                await _test()
                await assert_results(queue_outgoing, [])
                if use_debug_dir:
                    assert_debug_dir(
                        debug_dir,
                        FileType.TXT,
                        len([]),
                        ["in", "out", "stderrfile", "stdoutfile"],
                    )
        else:  # refresh_interval_rabbitmq_heartbeat_interval < TEST_1000_SLEEP
            await _test()
            await assert_results(queue_outgoing, msgs_outgoing_expected)
            if use_debug_dir:
                assert_debug_dir(
                    debug_dir,
                    FileType.TXT,
                    len(msgs_outgoing_expected),
                    ["in", "out", "stderrfile", "stdoutfile"],
                )

    # check for persisted files
    assert_versus_os_walk(
        first_walk,
        [debug_dir if use_debug_dir else Path("./tmp")],
    )
