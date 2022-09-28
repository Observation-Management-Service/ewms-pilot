"""Test pilot submodule."""

import os
from pathlib import Path

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


async def test_(
    queue_to_clients: str,  # pylint: disable=redefined-outer-name
    queue_from_clients: str,  # pylint: disable=redefined-outer-name
) -> None:
    """Test... something"""
    out_messages = [1, 2, 3, 4, 5]

    # populate queue
    to_client_q = mq.Queue(
        BROKER_CLIENT,
        address=BROKER_ADDRESS,
        name=queue_to_clients,
    )
    n_sent = 0
    async with to_client_q.open_pub() as pub:
        for msg in out_messages:
            await pub.send(msg)
            n_sent += 1
    assert n_sent == len(out_messages)

    # call consume_and_reply
    await consume_and_reply(
        cmd="TODO",
        broker_client=BROKER_CLIENT,
        broker_address=BROKER_ADDRESS,
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
    from_client_q = mq.Queue(
        BROKER_CLIENT,
        address=BROKER_ADDRESS,
        name=queue_from_clients,
    )
    n_received = 0
    async with from_client_q.open_sub() as sub:
        async for i, msg in asl.enumerate(sub):
            print(f"{i}: {msg}")
            n_received += 1
    assert n_received == len(out_messages)
