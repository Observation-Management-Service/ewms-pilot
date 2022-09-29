"""Test pilot submodule."""

import os
import time
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
    assert i+1 == len(msgs_to_subproc)

    # call consume_and_reply
    await consume_and_reply(
        cmd="""python3 -c "
output = open('in.txt').read().strip() * 2;
print(output, file=open('out.txt','w'))" """.replace('\n',' '),  # double cat
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
