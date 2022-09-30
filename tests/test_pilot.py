"""Test pilot submodule."""

import os
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, List, TypeVar

import asyncstdlib as asl
import mqclient as mq
import pytest
from ewms_pilot import consume_and_reply

BROKER_ADDRESS = "localhost"
BROKER_CLIENT = os.getenv("BROKER_CLIENT", "")


@pytest.fixture
def queue_to_clients() -> str:
    """Get the name of a queue for talking to client(s)."""
    return mq.Queue.make_name()


@pytest.fixture
def queue_from_clients() -> str:
    """Get the name of a queue for talking "from" client(s)."""
    return mq.Queue.make_name()


@pytest.fixture
def debug_dir() -> Path:
    """Make a unique debug directory and return its Path."""
    dirpath = Path(f"./debug-dir/{time.time()}")
    dirpath.mkdir(parents=True)
    return dirpath


async def populate_queue(
    queue_to_clients: str,  # pylint: disable=redefined-outer-name
    msgs_to_subproc: List,
) -> None:
    """Send messages to queue."""
    to_client_q = mq.Queue(
        BROKER_CLIENT,
        address=BROKER_ADDRESS,
        name=queue_to_clients,
    )
    async with to_client_q.open_pub() as pub:
        for i, msg in enumerate(msgs_to_subproc):
            await pub.send(msg)
    assert i + 1 == len(msgs_to_subproc)  # pylint:disable=undefined-loop-variable


T = TypeVar("T")


async def assert_results(
    queue_from_clients: str,  # pylint: disable=redefined-outer-name
    msgs_to_subproc: List[T],
    msgs_from_subproc: List[T],
) -> None:
    """Get messages and assert against expected results."""
    from_client_q = mq.Queue(
        BROKER_CLIENT,
        address=BROKER_ADDRESS,
        name=queue_from_clients,
    )
    received: List[T] = []
    async with from_client_q.open_sub() as sub:
        async for i, msg in asl.enumerate(sub):
            print(f"{i}: {msg}")
            received.append(msg)
    assert len(received) == len(msgs_to_subproc)

    if isinstance(msgs_from_subproc[0], dict):
        assert set(str(r) for r in received) == set(str(m) for m in msgs_from_subproc)
    else:
        assert set(received) == set(msgs_from_subproc)


def assert_debug_dir(
    debug_dir: Path,  # pylint: disable=redefined-outer-name
    fpath_to_subproc: Path,
    fpath_from_subproc: Path,
    msgs_from_subproc: List[T],
) -> None:
    assert len(list(debug_dir.iterdir())) == len(msgs_from_subproc)
    for path in debug_dir.iterdir():
        assert path.is_dir()
        for subpath in path.iterdir():
            assert subpath.is_file()
        assert [p.name for p in path.iterdir()] == [
            fpath_to_subproc,
            fpath_from_subproc,
        ]


########################################################################################


async def test_000__txt(
    queue_to_clients: str,  # pylint: disable=redefined-outer-name
    queue_from_clients: str,  # pylint: disable=redefined-outer-name
    debug_dir: Path,  # pylint:disable=redefined-outer-name
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    msgs_from_subproc = ["foofoo\n", "barbar\n", "bazbaz\n"]

    await populate_queue(queue_to_clients, msgs_to_subproc)

    await consume_and_reply(
        cmd="""python3 -c "
output = open('in.txt').read().strip() * 2;
print(output, file=open('out.txt','w'))" """,  # double cat
        broker_client=BROKER_CLIENT,
        broker_address=BROKER_ADDRESS,
        auth_token="",
        queue_to_clients=queue_to_clients,
        queue_from_clients=queue_from_clients,
        fpath_to_subproc=Path("in.txt"),
        fpath_from_subproc=Path("out.txt"),
        # file_writer=UniversalFileInterface.write, # see other tests
        # file_reader=UniversalFileInterface.read, # see other tests
        debug_dir=debug_dir,
    )

    await assert_results(queue_from_clients, msgs_to_subproc, msgs_from_subproc)
    assert_debug_dir(debug_dir, Path("in.txt"), Path("out.txt"), msgs_from_subproc)


async def test_001__txt(
    queue_to_clients: str,  # pylint: disable=redefined-outer-name
    queue_from_clients: str,  # pylint: disable=redefined-outer-name
    debug_dir: Path,  # pylint:disable=redefined-outer-name
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    msgs_from_subproc = ["foofoo\n", "barbar\n", "bazbaz\n"]

    await populate_queue(queue_to_clients, msgs_to_subproc)

    await consume_and_reply(
        cmd="""python3 -c "
output = open('in.txt').read().strip() * 2;
print(output, file=open('out.txt','w'))" """,  # double cat
        broker_client=BROKER_CLIENT,
        broker_address=BROKER_ADDRESS,
        auth_token="",
        queue_to_clients=queue_to_clients,
        queue_from_clients=queue_from_clients,
        # fpath_to_subproc=Path("in.txt"),
        # fpath_from_subproc=Path("out.txt"),
        # file_writer=UniversalFileInterface.write, # see other tests
        # file_reader=UniversalFileInterface.read, # see other tests
        debug_dir=debug_dir,
    )

    await assert_results(queue_from_clients, msgs_to_subproc, msgs_from_subproc)
    assert_debug_dir(debug_dir, Path("in.txt"), Path("out.txt"), msgs_from_subproc)


async def test_100__json(
    queue_to_clients: str,  # pylint: disable=redefined-outer-name
    queue_from_clients: str,  # pylint: disable=redefined-outer-name
    debug_dir: Path,  # pylint:disable=redefined-outer-name
) -> None:
    """Test a normal .json-based pilot."""
    # some messages that would make sense json'ing
    msgs_to_subproc = [{"attr-0": v} for v in ["foo", "bar", "baz"]]
    msgs_from_subproc = [{"attr-a": v, "attr-b": v + v} for v in ["foo", "bar", "baz"]]

    await populate_queue(queue_to_clients, msgs_to_subproc)

    await consume_and_reply(
        cmd="""python3 -c "
import json;
input=json.load(open('in.json'));
v=input['attr-0'];
output={'attr-a':v, 'attr-b':v+v};
json.dump(output, open('out.json','w'))" """,
        broker_client=BROKER_CLIENT,
        broker_address=BROKER_ADDRESS,
        auth_token="",
        queue_to_clients=queue_to_clients,
        queue_from_clients=queue_from_clients,
        fpath_to_subproc=Path("in.json"),
        fpath_from_subproc=Path("out.json"),
        # file_writer=UniversalFileInterface.write, # see other tests
        # file_reader=UniversalFileInterface.read, # see other tests
        debug_dir=debug_dir,
    )

    await assert_results(queue_from_clients, msgs_to_subproc, msgs_from_subproc)
    assert_debug_dir(debug_dir, Path("in.json"), Path("out.json"), msgs_from_subproc)


async def test_200__pickle(
    queue_to_clients: str,  # pylint: disable=redefined-outer-name
    queue_from_clients: str,  # pylint: disable=redefined-outer-name
    debug_dir: Path,  # pylint:disable=redefined-outer-name
) -> None:
    """Test a normal .pkl-based pilot."""
    # some messages that would make sense pickling
    msgs_to_subproc = [date(1995, 12, 3), date(2022, 9, 29), date(2063, 4, 5)]
    msgs_from_subproc = [d + timedelta(days=1) for d in msgs_to_subproc]

    await populate_queue(queue_to_clients, msgs_to_subproc)

    await consume_and_reply(
        cmd="""python3 -c "
import pickle;
from datetime import date, timedelta;
input=pickle.load(open('in.pkl','rb'));
output=input+timedelta(days=1);
pickle.dump(output, open('out.pkl','wb'))" """,
        broker_client=BROKER_CLIENT,
        broker_address=BROKER_ADDRESS,
        auth_token="",
        queue_to_clients=queue_to_clients,
        queue_from_clients=queue_from_clients,
        fpath_to_subproc=Path("in.pkl"),
        fpath_from_subproc=Path("out.pkl"),
        # file_writer=UniversalFileInterface.write, # see other tests
        # file_reader=UniversalFileInterface.read, # see other tests
        debug_dir=debug_dir,
    )

    await assert_results(queue_from_clients, msgs_to_subproc, msgs_from_subproc)
    assert_debug_dir(debug_dir, Path("in.pkl"), Path("out.pkl"), msgs_from_subproc)


async def test_300__writer_reader(
    queue_to_clients: str,  # pylint: disable=redefined-outer-name
    queue_from_clients: str,  # pylint: disable=redefined-outer-name
    debug_dir: Path,  # pylint:disable=redefined-outer-name
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    msgs_from_subproc = ["output: oofoof\n", "output: rabrab\n", "output: zabzab\n"]

    await populate_queue(queue_to_clients, msgs_to_subproc)

    def reverse_writer(text: Any, fpath: Path) -> None:
        with open(fpath, "w") as f:
            f.write(text[::-1])

    def reader_w_prefix(fpath: Path) -> str:
        with open(fpath) as f:
            return f"output: {f.read()}"

    await consume_and_reply(
        cmd="""python3 -c "
output = open('in.txt').read().strip() * 2;
print(output, file=open('out.txt','w'))" """,  # double cat
        broker_client=BROKER_CLIENT,
        broker_address=BROKER_ADDRESS,
        auth_token="",
        queue_to_clients=queue_to_clients,
        queue_from_clients=queue_from_clients,
        fpath_to_subproc=Path("in.txt"),
        fpath_from_subproc=Path("out.txt"),
        file_writer=reverse_writer,
        file_reader=reader_w_prefix,
        debug_dir=debug_dir,
    )

    await assert_results(queue_from_clients, msgs_to_subproc, msgs_from_subproc)
    assert_debug_dir(debug_dir, Path("in.txt"), Path("out.txt"), msgs_from_subproc)
