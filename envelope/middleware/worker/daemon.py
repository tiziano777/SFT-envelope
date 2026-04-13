"""Worker daemon: bootstrap, handshake, and state persistence."""

import asyncio
import logging
import json
from pathlib import Path
from typing import Optional
import httpx

from envelope.middleware.shared.envelopes import (
    HandshakeRequest,
    HandshakeResponse,
)
from envelope.middleware.shared.config_hasher import ConfigSnapshot
from envelope.middleware.shared.models import WorkerState, TransferLogEntry
from envelope.middleware.shared.state import AtomicStateManager

logger = logging.getLogger(__name__)


class WorkerDaemon:
    """Worker daemon: performs blocking handshake and persists state."""

    def __init__(
        self,
        setup_dir: Path,
        master_uri: str = "http://localhost:8000",
        api_key: str = "",
        handshake_timeout: int = 30,
    ):
        self.setup_dir = Path(setup_dir)
        self.master_uri = master_uri
        self.api_key = api_key
        self.handshake_timeout = handshake_timeout

        # State/marker files
        self.worker_dir = self.setup_dir / "worker"
        self.state_file = self.worker_dir / ".worker_state.json"
        self.exp_id_file = self.worker_dir / ".exp_id"
        self.handshake_done_file = self.worker_dir / ".handshake_done"
        self.transfer_log = self.worker_dir / "transfer_log.jsonl"

    async def bootstrap(self) -> Optional[WorkerState]:
        """Perform blocking handshake and persist state."""
        try:
            state = await self._handshake()
            if state:
                self._persist_state(state)
                logger.info(f"Handshake succeeded: exp_id={state.exp_id}")
                return state
            else:
                logger.warning("Handshake failed — entering degraded mode")
                return None
        except asyncio.TimeoutError:
            logger.warning(
                f"Handshake timeout ({self.handshake_timeout}s) — degraded mode"
            )
            return None
        except Exception as e:
            logger.error(f"Handshake error: {e}")
            return None

    async def _handshake(self) -> Optional[WorkerState]:
        """Blocking handshake with Master."""
        try:
            # Build handshake request
            config_snapshot = ConfigSnapshot.from_setup_dir(self.setup_dir)
            request = HandshakeRequest(
                recipe_id=config_snapshot.recipe_id or "unknown",
                config=config_snapshot,
            )

            async with httpx.AsyncClient() as client:
                resp = await asyncio.wait_for(
                    client.post(
                        f"{self.master_uri}/handshake",
                        json=request.model_dump(),
                        headers={"X-API-Key": self.api_key},
                    ),
                    timeout=self.handshake_timeout,
                )

                if resp.status_code == 200:
                    response = HandshakeResponse(**resp.json())
                    return WorkerState(
                        exp_id=response.exp_id,
                        recipe_id=request.recipe_id,
                        master_uri=self.master_uri,
                        strategy=response.strategy.value,
                    )
                else:
                    logger.error(
                        f"Handshake failed: status {resp.status_code}: {resp.text}"
                    )
                    return None

        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.error(f"Handshake HTTP error: {e}")
            return None

    def _persist_state(self, state: WorkerState) -> None:
        """Atomically persist state to files."""
        self.worker_dir.mkdir(parents=True, exist_ok=True)

        # Save .worker_state.json atomically
        state_dict = json.loads(state.model_dump_json(by_alias=True))
        AtomicStateManager.save(self.state_file, state_dict)

        # Write .exp_id marker
        self.exp_id_file.write_text(state.exp_id)

        # Write .handshake_done marker (empty file)
        self.handshake_done_file.touch()

        logger.info(f"State persisted: {self.state_file}")

    def log_transfer(self, entry: TransferLogEntry) -> None:
        """Append transfer log entry (idempotent)."""
        self.transfer_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.transfer_log, "a") as f:
            f.write(entry.model_dump_json() + "\n")
