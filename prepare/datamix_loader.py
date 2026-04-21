"""DatamixLoader: support for multi-source datasets with replica oversampling.

Note: Recipe schema is now canonical (RecipeConfig, RecipeEntry from config/models.py).
DatamixSource and DatamixConfig are deprecated aliases for backward compatibility.
"""

from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

from envelope.config.models import RecipeConfig, RecipeEntry

# Backward compatibility aliases
DatamixSource = RecipeEntry
DatamixConfig = RecipeConfig


class DatamixLoader:
    """Load and prepare datasets from datamix config."""

    def __init__(self, setup_dir: Path):
        self.setup_dir = Path(setup_dir)

    def load(self, config: Optional['DatamixConfig']) -> dict:
        """Load datamix configuration.

        Args:
            config: RecipeConfig or DatamixConfig (alias) with entries dict.

        Returns:
            Dict with total_samples and sources_info list.
        """
        if not config or not config.entries:
            raise ValueError("Datamix config must have entries")

        total_samples = 0
        sources_info = []

        for path, entry in config.entries.items():
            # entry is RecipeEntry
            source_samples = (entry.samples or 1000) * entry.replica
            total_samples += source_samples
            sources_info.append({
                "uri": entry.dist_uri,  # RecipeEntry uses dist_uri
                "replica": entry.replica,
                "samples": source_samples,
                "chat_type": entry.chat_type
            })

        return {
            "total_samples": total_samples,
            "sources": sources_info
        }
