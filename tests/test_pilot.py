"""Test pilot submodule."""

from pathlib import Path

import asyncstdlib as asl
from ewms_pilot import consume_and_reply
from ewms_pilot.mq import mq

BROKER = "localhost"


async def test_(queue_to_clients: str, queue_from_clients: str) -> None:
    """Test... something"""

    # populate queue
    to_client_q = mq.Queue(address=BROKER, name=queue_to_clients)
    async with to_client_q.open_pub() as pub:
        for out_msg in [1, 2, 3, 4, 5]:
            await pub.send(out_msg)

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
    from_client_q = mq.Queue(address=BROKER, name=queue_from_clients)
    async with from_client_q.open_sub() as sub:
        async for i, in_msg in asl.enumerate(sub):
            print(f"{i}: {in_msg}")
