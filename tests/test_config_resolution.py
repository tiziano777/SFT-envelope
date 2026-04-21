"""Integration tests for Phase 2: Config Resolution Refactor.

Verifies:
- Config.yaml includes all fields (hparam_overrides, diagnostics, etc.)
- Round-trip load→dump→reload produces identical config
- No load-time injection (all defaults from schema)
- Diagnostics optional via YAML
- resolve_hyperparams exists only in shared_utils (no template defs)
"""

from pathlib import Path

import pytest
import yaml

from envelope.config.defaults import HYPERPARAMETER_DEFAULTS
from envelope.config.loader import dump_config, load_config, load_yaml_config
from envelope.config.models import DiagnosticsConfig, EnvelopeConfig


EXAMPLE_CONFIGS = Path("configs/examples")


@pytest.fixture
def sft_config():
    """Load SFT baseline config."""
    path = EXAMPLE_CONFIGS / "sft_baseline.yaml"
    if not path.exists():
        pytest.skip(f"Config not found: {path}")
    return load_config(path)


@pytest.fixture
def grpo_config():
    """Load GRPO QLoRA config."""
    path = EXAMPLE_CONFIGS / "grpo_qlora_qwen.yaml"
    if not path.exists():
        pytest.skip(f"Config not found: {path}")
    return load_config(path)


class TestConfigComplete:
    """Generated config.yaml includes all fields with defaults."""

    def test_hparam_overrides_populated(self, sft_config):
        """hparam_overrides contains HYPERPARAMETER_DEFAULTS from schema."""
        assert sft_config.hparam_overrides is not None
        assert len(sft_config.hparam_overrides) >= len(HYPERPARAMETER_DEFAULTS)
        assert sft_config.hparam_overrides["learning_rate"] == 1e-5
        assert sft_config.hparam_overrides["per_device_train_batch_size"] == 2

    def test_diagnostics_field_present(self, sft_config):
        """DiagnosticsConfig populated with defaults."""
        assert isinstance(sft_config.diagnostics, DiagnosticsConfig)
        assert sft_config.diagnostics.enabled is True
        assert sft_config.diagnostics.callback_class == "TRLDiagnosticCallback"

    def test_dump_includes_all_fields(self, sft_config, tmp_path):
        """dump_config serializes all fields including defaults."""
        out = tmp_path / "config.yaml"
        dump_config(sft_config, out)
        data = yaml.safe_load(out.read_text())

        assert "hparam_overrides" in data
        assert "diagnostics" in data
        assert "training" in data
        assert data["diagnostics"]["enabled"] is True


class TestConfigRegenerable:
    """Loading generated config.yaml again produces identical EnvelopeConfig."""

    def test_round_trip(self, sft_config, tmp_path):
        """load→dump→reload = identical."""
        out = tmp_path / "config.yaml"
        dump_config(sft_config, out)

        reloaded = load_config(out)
        assert sft_config.model_dump() == reloaded.model_dump()

    def test_dump_idempotent(self, grpo_config, tmp_path):
        """dump→reload→dump = identical YAML."""
        out1 = tmp_path / "config1.yaml"
        dump_config(grpo_config, out1)

        reloaded = load_config(out1)
        out2 = tmp_path / "config2.yaml"
        dump_config(reloaded, out2)

        assert out1.read_text() == out2.read_text()


class TestNoLoaderInjection:
    """load_yaml_config doesn't inject defaults at load time."""

    def test_minimal_yaml_uses_schema_defaults(self):
        """Minimal YAML gets hparam_overrides from Pydantic Field defaults."""
        minimal = """
experiment:
  name: test
model:
  name_or_path: Qwen/Qwen2-1.5B
dataset:
  train_uri: ultrachat_200k
"""
        config = load_yaml_config(minimal)
        assert config.hparam_overrides["learning_rate"] == 1e-5
        assert config.diagnostics.enabled is True


class TestDiagnosticsOptional:
    """Diagnostics callback configurable via YAML."""

    def test_diagnostics_disabled(self):
        """Setting enabled=false disables diagnostics."""
        yml = """
experiment:
  name: test
model:
  name_or_path: Qwen/Qwen2-1.5B
dataset:
  train_uri: ultrachat_200k
diagnostics:
  enabled: false
"""
        config = load_yaml_config(yml)
        assert config.diagnostics.enabled is False

    def test_custom_callback(self):
        """Custom callback class configurable."""
        yml = """
experiment:
  name: test
model:
  name_or_path: Qwen/Qwen2-1.5B
dataset:
  train_uri: ultrachat_200k
diagnostics:
  enabled: true
  callback_class: CustomCallback
"""
        config = load_yaml_config(yml)
        assert config.diagnostics.callback_class == "CustomCallback"


class TestResolveHyperparamsSingleSource:
    """resolve_hyperparams not duplicated in templates."""

    def test_no_local_defs_in_templates(self):
        """No template file contains a local def resolve_hyperparams."""
        templates_dir = Path("generators/templates")
        if not templates_dir.exists():
            pytest.skip("Templates dir not found")

        for tmpl in templates_dir.glob("train_*.j2"):
            content = tmpl.read_text()
            assert "def resolve_hyperparams" not in content, (
                f"Template {tmpl.name} still has local resolve_hyperparams definition"
            )
