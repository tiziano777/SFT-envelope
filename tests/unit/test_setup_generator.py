"""Unit tests for envelope/generators/setup_generator.py."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from envelope.generators.setup_generator import generate_setup

# Absolute path to the example config files
CONFIGS_DIR = Path(__file__).resolve().parents[2] / "configs" / "examples"
GRPO_CONFIG = CONFIGS_DIR / "grpo_qlora_qwen.yaml"
SFT_CONFIG = CONFIGS_DIR / "sft_lora_llama3.yaml"


class TestGenerateSetupGRPO:
    """Test setup generation from the GRPO example config."""

    @pytest.fixture()
    def setup_dir(self, tmp_path: Path) -> Path:
        return generate_setup(
            config_path=GRPO_CONFIG,
            name="grpo-test",
            output_base=tmp_path,
        )

    def test_returns_path(self, setup_dir: Path):
        assert isinstance(setup_dir, Path)
        assert setup_dir.exists()
        assert setup_dir.is_dir()

    def test_directory_name(self, setup_dir: Path):
        assert setup_dir.name == "setup_grpo-test"

    def test_contains_train_py(self, setup_dir: Path):
        train_py = setup_dir / "train.py"
        assert train_py.exists()
        assert train_py.stat().st_size > 0

    def test_contains_run_sh(self, setup_dir: Path):
        run_sh = setup_dir / "run.sh"
        assert run_sh.exists()
        # Check executable
        assert os.access(run_sh, os.X_OK)

    def test_contains_config_yaml(self, setup_dir: Path):
        config_yaml = setup_dir / "config.yaml"
        assert config_yaml.exists()
        assert config_yaml.stat().st_size > 0

    def test_contains_requirements_txt(self, setup_dir: Path):
        req_txt = setup_dir / "requirements.txt"
        assert req_txt.exists()
        assert req_txt.stat().st_size > 0

    def test_train_py_mentions_model(self, setup_dir: Path):
        content = (setup_dir / "train.py").read_text()
        assert "Qwen/Qwen2.5-7B-Instruct" in content

    def test_train_py_imports_grpo(self, setup_dir: Path):
        content = (setup_dir / "train.py").read_text()
        assert "GRPOTrainer" in content or "GRPOConfig" in content

    def test_train_py_has_peft_config(self, setup_dir: Path):
        content = (setup_dir / "train.py").read_text()
        assert "LoraConfig" in content

    def test_train_py_has_reward_function(self, setup_dir: Path):
        content = (setup_dir / "train.py").read_text()
        assert "reward_function" in content or "reward_funcs" in content

    def test_run_sh_mentions_technique(self, setup_dir: Path):
        content = (setup_dir / "run.sh").read_text()
        assert "grpo" in content.lower()

    def test_run_sh_mentions_framework(self, setup_dir: Path):
        content = (setup_dir / "run.sh").read_text()
        assert "trl" in content.lower()

    def test_requirements_contain_trl(self, setup_dir: Path):
        content = (setup_dir / "requirements.txt").read_text()
        assert "trl" in content

    def test_requirements_contain_peft(self, setup_dir: Path):
        content = (setup_dir / "requirements.txt").read_text()
        assert "peft" in content

    def test_requirements_contain_bitsandbytes(self, setup_dir: Path):
        content = (setup_dir / "requirements.txt").read_text()
        assert "bitsandbytes" in content

    def test_config_yaml_valid(self, setup_dir: Path):
        """Saved config should be re-loadable YAML."""
        import yaml

        config_yaml = setup_dir / "config.yaml"
        with open(config_yaml) as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert data["experiment"]["name"] == "grpo-qlora-qwen-math"
        assert data["training"]["technique"] == "grpo"


class TestGenerateSetupSFT:
    """Test setup generation from the SFT example config."""

    @pytest.fixture()
    def setup_dir(self, tmp_path: Path) -> Path:
        return generate_setup(
            config_path=SFT_CONFIG,
            name="sft-test",
            output_base=tmp_path,
        )

    def test_returns_path(self, setup_dir: Path):
        assert isinstance(setup_dir, Path)
        assert setup_dir.exists()

    def test_directory_name(self, setup_dir: Path):
        assert setup_dir.name == "setup_sft-test"

    def test_all_required_files_present(self, setup_dir: Path):
        for filename in ("train.py", "run.sh", "config.yaml", "requirements.txt"):
            assert (setup_dir / filename).exists(), f"Missing {filename}"

    def test_train_py_mentions_model(self, setup_dir: Path):
        content = (setup_dir / "train.py").read_text()
        assert "meta-llama/Llama-3.1-8B-Instruct" in content

    def test_train_py_imports_sft(self, setup_dir: Path):
        content = (setup_dir / "train.py").read_text()
        assert "SFTTrainer" in content or "SFTConfig" in content

    def test_train_py_has_peft_config(self, setup_dir: Path):
        content = (setup_dir / "train.py").read_text()
        assert "LoraConfig" in content

    def test_train_py_has_packing(self, setup_dir: Path):
        """SFT config has sequence_packing=true, so the template should reference packing."""
        content = (setup_dir / "train.py").read_text()
        assert "packing" in content.lower()

    def test_run_sh_mentions_technique(self, setup_dir: Path):
        content = (setup_dir / "run.sh").read_text()
        assert "sft" in content.lower()

    def test_config_yaml_preserves_technique(self, setup_dir: Path):
        import yaml

        with open(setup_dir / "config.yaml") as f:
            data = yaml.safe_load(f)
        assert data["training"]["technique"] == "sft"

    def test_no_rewards_dir(self, setup_dir: Path):
        """SFT does not need reward functions, so no rewards/ dir should be created."""
        assert not (setup_dir / "rewards").exists()


class TestGenerateSetupIdempotent:
    """Generating a setup into the same directory twice should succeed (overwrite)."""

    def test_overwrite(self, tmp_path: Path):
        dir1 = generate_setup(SFT_CONFIG, name="idem", output_base=tmp_path)
        dir2 = generate_setup(SFT_CONFIG, name="idem", output_base=tmp_path)
        assert dir1 == dir2
        assert (dir2 / "train.py").exists()
