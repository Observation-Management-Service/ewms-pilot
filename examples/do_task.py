"""A simple example script (task) to run on worker.

See https://github.com/Observation-Management-Service/ewms-workflow-management-service/blob/main/examples/request_task.py
"""

import asyncio
import logging

from ewms_pilot import consume_and_reply

LOGGER = logging.getLogger(__name__)


async def main() -> None:
    """Test a normal .txt-based pilot."""

    await consume_and_reply(
        # task is to "double" the input, one-at-a-time
        "python:alpine",
        """python3 -c "
import sys
import time
import argparse
import os
print('this is a log', file=sys.stderr)
output = open('{{INFILE}}').read().strip() * 2
time.sleep(5)
print('printed: ' + output)
print(output, file=open('{{OUTFILE}}','w'))
" """,
    )


if __name__ == "__main__":
    asyncio.run(main())
