"""Housekeeping logic."""


import asyncio
import time

import mqclient as mq

from .config import LOGGER


class Housekeeping:
    """Manage and perform housekeeping."""

    RABBITMQ_HEARTBEAT_INTERVAL = 5

    def __init__(self) -> None:
        self.prev_rabbitmq_heartbeat = 0.0

    async def basic_housekeeping(
        self,
    ) -> None:
        """Do basic housekeeping."""
        await asyncio.sleep(0)  # hand over control to other async tasks

        # TODO -- add other housekeeping

    async def queue_housekeeping(
        self,
        in_queue: mq.Queue,
        sub: mq.queue.ManualQueueSubResource,
        pub: mq.queue.QueuePubResource,
    ) -> None:
        """Do housekeeping for queue + basic housekeeping."""
        await self.basic_housekeeping()

        # rabbitmq heartbeats
        # TODO: replace when https://github.com/Observation-Management-Service/MQClient/issues/56
        if in_queue._broker_client.NAME.lower() == "rabbitmq":
            if (
                time.time() - self.prev_rabbitmq_heartbeat
                > self.RABBITMQ_HEARTBEAT_INTERVAL
            ):
                self.prev_rabbitmq_heartbeat = time.time()
                for raw_q in [pub.pub, sub._sub]:
                    if raw_q.connection:  # type: ignore[attr-defined, union-attr]
                        LOGGER.info("sending heartbeat to RabbitMQ broker...")
                        raw_q.connection.process_data_events()  # type: ignore[attr-defined, union-attr]

        # TODO -- add other housekeeping
