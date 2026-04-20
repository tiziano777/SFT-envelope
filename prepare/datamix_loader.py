"""DatamixLoader: support for multi-source datasets with replica oversampling."""

from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field


class DatamixSource(BaseModel):
    """Single data source in a datamix."""
    uri: str = Field(..., description="Data source URI")
    replica: int = Field(1, ge=1, description="Times to repeat this source")
    samples: int = Field(0, ge=0, description="Limit to N samples (0=all)")
    dist_name: Optional[str] = None
    chat_type: str = "instruct"


class DatamixConfig(BaseModel):
    """Multi-source dataset configuration."""
    sources: List[DatamixSource] = Field(..., min_items=1)


class DatamixLoader:
    """Load and prepare datasets from datamix config."""

    def __init__(self, setup_dir: Path):
        self.setup_dir = Path(setup_dir)

    def load(self, config: Optional['DatamixConfig']) -> dict:
        """Load datamix configuration."""
        if not config or not config.sources:
            raise ValueError("Datamix config must have sources")

        total_samples = 0
        sources_info = []

        for source in config.sources:
            source_samples = (source.samples or 1000) * source.replica
            total_samples += source_samples
            sources_info.append({
                "uri": source.uri,
                "replica": source.replica,
                "samples": source_samples,
                "chat_type": source.chat_type
            })

        return {
            "total_samples": total_samples,
            "sources": sources_info
        }
