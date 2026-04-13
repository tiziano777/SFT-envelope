"""Tests for Datamix support."""

import pytest
from envelope.prepare.datamix_loader import DatamixSource, DatamixConfig, DatamixLoader
from pathlib import Path


@pytest.fixture
def datamix_config():
    """Sample datamix config."""
    return DatamixConfig(sources=[
        DatamixSource(uri="file://data1.parquet", replica=1, samples=100),
        DatamixSource(uri="file://data2.parquet", replica=2, samples=50),
    ])


def test_datamix_source_validation():
    """DatamixSource validates fields."""
    source = DatamixSource(uri="s3://bucket/data.parquet", replica=2)
    assert source.replica == 2
    assert source.chat_type == "instruct"


def test_datamix_config_multiple_sources(datamix_config):
    """DatamixConfig contains multiple sources."""
    assert len(datamix_config.sources) == 2
    assert datamix_config.sources[0].uri == "file://data1.parquet"
    assert datamix_config.sources[1].replica == 2


def test_datamix_loader_calculates_totals(tmp_path):
    """DatamixLoader calculates total samples with replica."""
    config = DatamixConfig(sources=[
        DatamixSource(uri="file://data.parquet", replica=1, samples=100),
        DatamixSource(uri="file://data2.parquet", replica=2, samples=50),
    ])

    loader = DatamixLoader(tmp_path)
    result = loader.load(config)

    assert result["total_samples"] == 200
    assert len(result["sources"]) == 2


def test_datamix_loader_default_samples():
    """DatamixLoader uses default 1000 samples if not specified."""
    config = DatamixConfig(sources=[
        DatamixSource(uri="file://data.parquet", replica=1),
    ])

    loader = DatamixLoader(Path("/tmp"))
    result = loader.load(config)

    assert result["sources"][0]["samples"] == 1000


def test_datamix_replica_oversampling():
    """Replica field multiplies samples."""
    config = DatamixConfig(sources=[
        DatamixSource(uri="file://data.parquet", replica=3, samples=10),
    ])

    loader = DatamixLoader(Path("/tmp"))
    result = loader.load(config)

    assert result["sources"][0]["samples"] == 30


def test_error_on_empty_datamix():
    """Error when datamix has no sources."""
    with pytest.raises(ValueError):
        DatamixConfig(sources=[])


def test_error_on_none_datamix(tmp_path):
    """Error when loading None datamix."""
    loader = DatamixLoader(tmp_path)

    with pytest.raises(ValueError):
        loader.load(None)


def test_datamix_source_chat_type():
    """DatamixSource supports chat_type field."""
    source = DatamixSource(
        uri="s3://data.parquet",
        replica=1,
        chat_type="multi_turn"
    )

    assert source.chat_type == "multi_turn"
