"""Test pilot submodule."""

import os
import time
from datetime import date, timedelta
from pathlib import Path
from typing import List

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


async def test_txt(
    queue_to_clients: str,  # pylint: disable=redefined-outer-name
    queue_from_clients: str,  # pylint: disable=redefined-outer-name
    debug_dir: Path,  # pylint:disable=redefined-outer-name
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]
    msgs_from_subproc = ["foofoo\n", "barbar\n", "bazbaz\n"]

    # populate queue
    to_client_q = mq.Queue(
        BROKER_CLIENT,
        address=BROKER_ADDRESS,
        name=queue_to_clients,
    )
    async with to_client_q.open_pub() as pub:
        for i, msg in enumerate(msgs_to_subproc):
            await pub.send(msg)
    assert i + 1 == len(msgs_to_subproc)

    # call consume_and_reply
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
        # file_writer=UniversalFileInterface.write, # TODO in diff test
        # file_reader=UniversalFileInterface.read, # TODO in diff test
        debug_dir=debug_dir,
    )

    # assert results
    from_client_q = mq.Queue(
        BROKER_CLIENT,
        address=BROKER_ADDRESS,
        name=queue_from_clients,
    )
    received: List[str] = []
    async with from_client_q.open_sub() as sub:
        async for i, msg in asl.enumerate(sub):
            print(f"{i}: {msg}")
            received.append(msg)
    assert len(received) == len(msgs_to_subproc)
    assert set(received) == set(msgs_from_subproc)


async def test_json(
    queue_to_clients: str,  # pylint: disable=redefined-outer-name
    queue_from_clients: str,  # pylint: disable=redefined-outer-name
    debug_dir: Path,  # pylint:disable=redefined-outer-name
) -> None:
    """Test a normal .json-based pilot."""
    # some messages that would make sense json'ing
    msgs_to_subproc = [{"attr-0": v} for v in ["foo", "bar", "baz"]]
    msgs_from_subproc = [{"attr-a": v, "attr-b": v + v} for v in ["foo", "bar", "baz"]]

    # populate queue
    to_client_q = mq.Queue(
        BROKER_CLIENT,
        address=BROKER_ADDRESS,
        name=queue_to_clients,
    )
    async with to_client_q.open_pub() as pub:
        for i, msg in enumerate(msgs_to_subproc):
            await pub.send(msg)
    assert i + 1 == len(msgs_to_subproc)

    # call consume_and_reply
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
        # file_writer=UniversalFileInterface.write, # TODO in diff test
        # file_reader=UniversalFileInterface.read, # TODO in diff test
        debug_dir=debug_dir,
    )

    # assert results
    from_client_q = mq.Queue(
        BROKER_CLIENT,
        address=BROKER_ADDRESS,
        name=queue_from_clients,
    )
    received: List[dict] = []
    async with from_client_q.open_sub() as sub:
        async for i, msg in asl.enumerate(sub):
            print(f"{i}: {msg}")
            received.append(msg)
    assert len(received) == len(msgs_to_subproc)
    assert set(received) == set(msgs_from_subproc)


async def test_pickle(
    queue_to_clients: str,  # pylint: disable=redefined-outer-name
    queue_from_clients: str,  # pylint: disable=redefined-outer-name
    debug_dir: Path,  # pylint:disable=redefined-outer-name
) -> None:
    """Test a normal .pkl-based pilot."""
    # some messages that would make sense pickling
    msgs_to_subproc = [date(1995, 12, 3), date(2022, 9, 29), date(2063, 4, 5)]
    msgs_from_subproc = [d + timedelta(days=1) for d in msgs_to_subproc]

    # populate queue
    to_client_q = mq.Queue(
        BROKER_CLIENT,
        address=BROKER_ADDRESS,
        name=queue_to_clients,
    )
    async with to_client_q.open_pub() as pub:
        for i, msg in enumerate(msgs_to_subproc):
            await pub.send(msg)
    assert i + 1 == len(msgs_to_subproc)

    # call consume_and_reply
    await consume_and_reply(
        cmd="""python3 -c "
import pickle;
from datetime import date, timedelta;
input=pickle.load(open('in.pkl','rb'));
output=d+timedelta(days=1);
pickle.dump(output, open('out.pkl','wb'))" """,
        broker_client=BROKER_CLIENT,
        broker_address=BROKER_ADDRESS,
        auth_token="",
        queue_to_clients=queue_to_clients,
        queue_from_clients=queue_from_clients,
        fpath_to_subproc=Path("in.pkl"),
        fpath_from_subproc=Path("out.pkl"),
        # file_writer=UniversalFileInterface.write, # TODO in diff test
        # file_reader=UniversalFileInterface.read, # TODO in diff test
        debug_dir=debug_dir,
    )

    # assert results
    from_client_q = mq.Queue(
        BROKER_CLIENT,
        address=BROKER_ADDRESS,
        name=queue_from_clients,
    )
    received: List[date] = []
    async with from_client_q.open_sub() as sub:
        async for i, msg in asl.enumerate(sub):
            print(f"{i}: {msg}")
            received.append(msg)
    assert len(received) == len(msgs_to_subproc)
    assert set(received) == set(msgs_from_subproc)
