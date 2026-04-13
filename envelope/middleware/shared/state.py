"""Atomic state persistence utilities."""

import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any


class AtomicStateManager:
    """Atomic file write using tmp + rename pattern."""

    @staticmethod
    def save(path: Path, obj: dict) -> None:
        """Save JSON atomically using tmp file + rename."""
        path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            mode="w",
            delete=False,
            suffix=".tmp",
        ) as tmp:
            json.dump(obj, tmp, default=str)
            tmp_path = Path(tmp.name)

        # Atomic rename
        tmp_path.replace(path)

    @staticmethod
    def load(path: Path) -> Optional[Dict[str, Any]]:
        """Load JSON or return None if not exists."""
        if path.exists():
            return json.loads(path.read_text())
        return None
