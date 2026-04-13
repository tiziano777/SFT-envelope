"""Async event pusher with exponential backoff retry."""

import asyncio
import logging
from pathlib import Path
from typing import Set, Optional
from datetime import datetime, timedelta

from ..shared.connection import BaseConnection
from ..shared.models import TransferLogEntry

logger = logging.getLogger(__name__)


class AsyncPusher:
    """Queue-based async event pusher with exponential backoff retry."""

    def __init__(self,
                 connection: BaseConnection,
                 transfer_log: Path,
                 max_retries: int = 5,
                 initial_backoff: float = 1.0):
        self.connection = connection
        self.transfer_log = transfer_log
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.queue = asyncio.Queue()
        self.seen_ids: Set[str] = set()
        self._running = False

    async def push_event(self, event_id: str, event_type: str, data: dict) -> None:
        """Deduplicate and queue event for pushing."""
        if event_id in self.seen_ids:
            logger.debug(f"Skipping duplicate event {event_id}")
            return

        self.seen_ids.add(event_id)
        await self.queue.put({
            "event_id": event_id,
            "event_type": event_type,
            "data": data,
            "retry_count": 0
        })

    async def start(self, timeout: float = 10.0) -> None:
        """Start pusher worker loop."""
        self._running = True
        deadline = datetime.now() + timedelta(seconds=timeout)

        while self._running and datetime.now() < deadline:
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            await self._push_with_retry(item)

    async def _push_with_retry(self, item: dict) -> None:
        """Push event with exponential backoff retry."""
        event_id = item["event_id"]

        for attempt in range(self.max_retries):
            if attempt > 0:
                backoff = self.initial_backoff * (2 ** (attempt - 1))
                logger.info(f"Retry {attempt}/{self.max_retries} for {event_id}")
                await asyncio.sleep(backoff)

            try:
                success = await self.connection.send_metadata(item["data"])
                if success:
                    self._log_transfer(event_id, item["event_type"], "sent")
                    return
            except Exception as e:
                logger.warning(f"Push attempt {attempt} failed: {e}")

        # Exhausted retries
        self._log_transfer(event_id, item["event_type"], "failed")

    def _log_transfer(self,
                      event_id: str,
                      event_type: str,
                      status: str,
                      error: Optional[str] = None) -> None:
        """Append to transfer log."""
        entry = TransferLogEntry(
            event_id=event_id,
            event_type=event_type,
            status=status,
            error=error
        )
        self.transfer_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.transfer_log, 'a') as f:
            f.write(entry.model_dump_json() + '\n')

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
