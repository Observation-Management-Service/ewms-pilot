"""Test pilot submodule."""

from pathlib import Path

import asyncstdlib as asl
import pytest
from ewms_pilot import consume_and_reply
from ewms_pilot.mq import mq

BROKER = "localhost"


@pytest.fixture
def queue_to_clients() -> str:
    """Get the name of a queue for talking to client(s)."""
    return mq.Queue.make_name()


@pytest.fixture
def queue_from_clients() -> str:
    """Get the name of a queue for talking "from" client(s)."""
    return mq.Queue.make_name()


async def test_(
    queue_to_clients: str,  # pylint: disable=redefined-outer-name
    queue_from_clients: str,  # pylint: disable=redefined-outer-name
) -> None:
    """Test... something"""

    # populate queue
    msgs_sent = 0
    to_client_q = mq.Queue(address=BROKER, name=queue_to_clients)
    async with to_client_q.open_pub() as pub:
        for out_msg in [1, 2, 3, 4, 5]:
            await pub.send(out_msg)
            msgs_sent += 1
    assert msgs_sent

    # call consume_and_reply
    await consume_and_reply(
        cmd="TODO",
        broker=BROKER,
        auth_token="",
        queue_to_clients=queue_to_clients,
        queue_from_clients=queue_from_clients,
        fpath_to_client=Path("in.txt"),  # TODO in diff test
        fpath_from_client=Path("out.txt"),  # TODO in diff test
        # file_writer=UniversalFileInterface.write, # TODO in diff test
        # file_reader=UniversalFileInterface.read, # TODO in diff test
        debug_dir=Path("./TODO/"),  # TODO
    )

    # assert results
    msgs_received = 0
    from_client_q = mq.Queue(address=BROKER, name=queue_from_clients)
    async with from_client_q.open_sub() as sub:
        async for i, in_msg in asl.enumerate(sub):
            print(f"{i}: {in_msg}")
            msgs_received += 1
    assert msgs_received

    assert msgs_sent == msgs_received
