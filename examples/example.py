"""A simple example script to see EWMS pilot in real-time."""


import asyncio
from pathlib import Path

import mqclient as mq
import wipac_dev_tools
from ewms_pilot import FileType, config, consume_and_reply


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
output = open('{{INFILE}}').read().strip() * 2
time.sleep(5)
print('printed: ' + output)
print(output, file=open('{{OUTFILE}}','w'))
time.sleep(5)
" """,
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
    )


if __name__ == "__main__":
    wipac_dev_tools.logging_tools.set_level("DEBUG", first_party_loggers=["ewms-pilot"])

    asyncio.run(
        main(
            mq.Queue.make_name(),
            mq.Queue.make_name(),
            Path("."),
        )
    )
