"""HTTP connection to Master."""

import httpx
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from ..shared.connection import BaseConnection

logger = logging.getLogger(__name__)


class HTTPConnection(BaseConnection):
    """Connection to Master via HTTP REST."""

    def __init__(self, master_uri: str, api_key: str, timeout: int = 30):
        self.master_uri = master_uri
        self.api_key = api_key
        self.timeout = timeout

    async def send_metadata(self, data: Dict[str, Any]) -> bool:
        """POST metadata to /sync_event endpoint."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.master_uri}/sync_event",
                    json=data,
                    headers={"X-API-Key": self.api_key},
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Metadata send failed: {e}")
            return False

    async def transfer_file(self, local_path: Path, remote_uri: str) -> bool:
        """Upload file to Master storage via /checkpoint_push."""
        try:
            with open(local_path, "rb") as f:
                content = f.read()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.master_uri}/checkpoint_push",
                    content=content,
                    headers={
                        "X-API-Key": self.api_key,
                        "X-URI": remote_uri,
                    },
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"File transfer failed: {e}")
            return False

    async def health_check(self) -> bool:
        """GET /health to verify Master availability."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{self.master_uri}/health",
                    headers={"X-API-Key": self.api_key},
                )
                return resp.status_code == 200
        except Exception:
            return False
