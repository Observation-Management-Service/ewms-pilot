"""A simple example script to see EWMS pilot in real-time."""


import asyncio
from pathlib import Path

import mqclient as mq
from ewms_pilot import config, consume_and_reply


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


async def main(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
) -> None:
    """Test a normal .txt-based pilot."""
    msgs_to_subproc = ["foo", "bar", "baz"]

    await populate_queue(queue_incoming, msgs_to_subproc)

    await consume_and_reply(
        # double cat
        cmd="""python3 -c "
import sys
import time
time.sleep(5)
print('this is a log', file=sys.stderr)
time.sleep(5)
output = open('in.txt').read().strip() * 2
time.sleep(5)
print('printed: ' + output)
print(output, file=open('out.txt','w'))
time.sleep(5)
" """,
        # broker_client=,  # rely on env var
        # broker_address=,  # rely on env var
        # auth_token="",
        queue_incoming=queue_incoming,
        queue_outgoing=queue_outgoing,
        fpath_to_subproc=Path("in.txt"),
        fpath_from_subproc=Path("out.txt"),
        # file_writer=UniversalFileInterface.write, # see other tests
        # file_reader=UniversalFileInterface.read, # see other tests
        debug_dir=debug_dir,
    )


if __name__ == "__main__":
    asyncio.run(
        main(
            mq.Queue.make_name(),
            mq.Queue.make_name(),
            Path("."),
        )
    )
