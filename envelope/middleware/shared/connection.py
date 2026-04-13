"""Base connection interface for communicating with Master."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path


class BaseConnection(ABC):
    """Base class for communication with Master."""

    @abstractmethod
    async def send_metadata(self, data: Dict[str, Any]) -> bool:
        """Send metadata to Master. Returns True on success."""
        pass

    @abstractmethod
    async def transfer_file(self, local_path: Path, remote_uri: str) -> bool:
        """Transfer file to Master storage. Returns True on success."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify connection to Master. Returns True if healthy."""
        pass
