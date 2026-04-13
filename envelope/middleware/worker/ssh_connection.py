"""SSH connection stub (future implementation)."""

from pathlib import Path
from typing import Optional, Dict, Any

from ..shared.connection import BaseConnection


class SSHConnection(BaseConnection):
    """Connection to Master via SSH + SCP (stub for Phase 7)."""

    def __init__(self, host: str, user: str, key_path: Optional[Path] = None):
        self.host = host
        self.user = user
        self.key_path = key_path

    async def send_metadata(self, data: Dict[str, Any]) -> bool:
        raise NotImplementedError("SSH metadata — Phase 7")

    async def transfer_file(self, local_path: Path, remote_uri: str) -> bool:
        raise NotImplementedError("SSH file transfer — Phase 7")

    async def health_check(self) -> bool:
        raise NotImplementedError("SSH health check — Phase 7")
