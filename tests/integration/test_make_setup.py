"""Integration test: load YAML -> validate -> generate -> verify output files."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from envelope.config.loader import load_config
from envelope.config.validators import validate_config, validate_config_or_raise
from envelope.generators.setup_generator import generate_setup

CONFIGS_DIR = Path(__file__).resolve().parents[2] / "configs" / "examples"
GRPO_CONFIG = CONFIGS_DIR / "grpo_qlora_qwen.yaml"
SFT_CONFIG = CONFIGS_DIR / "sft_lora_llama3.yaml"


# ---------------------------------------------------------------------------
# Parametrized integration tests for both example configs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "config_path,setup_name,expected_technique,expected_framework",
    [
        (GRPO_CONFIG, "int-grpo", "grpo", "trl"),
        (SFT_CONFIG, "int-sft", "sft", "trl"),
    ],
    ids=["grpo-qlora-qwen", "sft-lora-llama3"],
)
class TestEndToEndSetupGeneration:
    """Full pipeline: YAML -> load -> validate -> generate -> verify."""

    @pytest.fixture()
    def setup_dir(
        self,
        tmp_path: Path,
        config_path: Path,
        setup_name: str,
        expected_technique: str,
        expected_framework: str,
    ) -> Path:
        return generate_setup(
            config_path=config_path,
            name=setup_name,
            output_base=tmp_path,
        )

    # -- Step 1: Config loading -------------------------------------------------

    def test_config_loads_successfully(
        self, config_path, setup_name, expected_technique, expected_framework
    ):
        config = load_config(config_path)
        assert config.training.technique.value == expected_technique
        assert config.framework.backend.value == expected_framework

    def test_config_validates_cleanly(
        self, config_path, setup_name, expected_technique, expected_framework
    ):
        config = load_config(config_path)
        # validate_config_or_raise should not raise for example configs
        validate_config_or_raise(config)

    def test_validate_config_returns_acceptable_errors(
        self, config_path, setup_name, expected_technique, expected_framework
    ):
        """Example configs may have soft warnings (e.g., RL without reward functions for GRPO).

        We check that there are no framework/hardware hard errors.
        """
        config = load_config(config_path)
        errors = validate_config(config)
        hard_errors = [
            e
            for e in errors
            if "does not support" in e.lower() or "not supported" in e.lower()
        ]
        assert len(hard_errors) == 0, f"Unexpected hard errors: {hard_errors}"

    # -- Step 2: Directory structure -------------------------------------------

    def test_setup_dir_exists(
        self, setup_dir, config_path, setup_name, expected_technique, expected_framework
    ):
        assert setup_dir.exists()
        assert setup_dir.is_dir()

    @pytest.mark.parametrize(
        "filename",
        ["train.py", "run.sh", "config.yaml", "requirements.txt"],
    )
    def test_required_file_exists(
        self,
        setup_dir,
        filename,
        config_path,
        setup_name,
        expected_technique,
        expected_framework,
    ):
        assert (setup_dir / filename).exists(), f"Missing {filename} in {setup_dir}"

    def test_train_py_non_empty(
        self, setup_dir, config_path, setup_name, expected_technique, expected_framework
    ):
        content = (setup_dir / "train.py").read_text()
        assert len(content) > 100

    def test_run_sh_executable(
        self, setup_dir, config_path, setup_name, expected_technique, expected_framework
    ):
        import os

        assert os.access(setup_dir / "run.sh", os.X_OK)

    # -- Step 3: Content checks ------------------------------------------------

    def test_config_yaml_round_trip(
        self, setup_dir, config_path, setup_name, expected_technique, expected_framework
    ):
        """The saved config.yaml should parse and contain the correct technique."""
        with open(setup_dir / "config.yaml") as f:
            data = yaml.safe_load(f)
        assert data["training"]["technique"] == expected_technique
        assert data["framework"]["backend"] == expected_framework

    def test_requirements_txt_has_torch(
        self, setup_dir, config_path, setup_name, expected_technique, expected_framework
    ):
        content = (setup_dir / "requirements.txt").read_text()
        assert "torch" in content

    def test_run_sh_has_launch_command(
        self, setup_dir, config_path, setup_name, expected_technique, expected_framework
    ):
        content = (setup_dir / "run.sh").read_text()
        # Should contain python, accelerate, bash, tune, or llamafactory-cli
        assert any(
            kw in content for kw in ("python", "accelerate", "bash", "tune", "llamafactory")
        )

    def test_train_py_has_envelope_header(
        self, setup_dir, config_path, setup_name, expected_technique, expected_framework
    ):
        content = (setup_dir / "train.py").read_text()
        assert "FineTuning-Envelope" in content or "Auto-generated" in content


# ---------------------------------------------------------------------------
# Standalone integration: GRPO-specific deep checks
# ---------------------------------------------------------------------------


class TestGRPODeepIntegration:
    """Deeper checks on the GRPO setup output."""

    @pytest.fixture()
    def setup_dir(self, tmp_path: Path) -> Path:
        return generate_setup(GRPO_CONFIG, name="deep-grpo", output_base=tmp_path)

    def test_frozen_config_preserves_all_sections(self, setup_dir: Path):
        with open(setup_dir / "config.yaml") as f:
            data = yaml.safe_load(f)
        required_sections = [
            "experiment",
            "model",
            "training",
            "dataset",
            "reward",
            "hardware",
            "optimization",
            "framework",
            "output",
        ]
        for section in required_sections:
            assert section in data, f"Missing section: {section}"

    def test_frozen_config_peft_details(self, setup_dir: Path):
        with open(setup_dir / "config.yaml") as f:
            data = yaml.safe_load(f)
        peft = data["training"]["peft"]
        assert peft["method"] == "qlora"
        assert peft["r"] == 32
        assert peft["lora_alpha"] == 64

    def test_frozen_config_reward_functions(self, setup_dir: Path):
        with open(setup_dir / "config.yaml") as f:
            data = yaml.safe_load(f)
        functions = data["reward"]["functions"]
        assert len(functions) == 2
        assert functions[0]["name"] == "math_correctness"
        assert functions[1]["name"] == "format_check"

    def test_train_py_mentions_dataset(self, setup_dir: Path):
        content = (setup_dir / "prepare.py").read_text()
        assert "argilla/magpie-ultra-v1.0" in content

    def test_train_py_has_hyperparams(self, setup_dir: Path):
        content = (setup_dir / "train.py").read_text()
        assert "HYPERPARAM_DEFAULTS" in content
        assert "learning_rate" in content

    def test_train_py_has_structured_output(self, setup_dir: Path):
        content = (setup_dir / "train.py").read_text()
        assert "EXPERIMENT_STATUS" in content

    def test_requirements_contain_flash_attn(self, setup_dir: Path):
        content = (setup_dir / "requirements.txt").read_text()
        assert "flash-attn" in content


# ---------------------------------------------------------------------------
# Standalone integration: SFT-specific deep checks
# ---------------------------------------------------------------------------


class TestSFTDeepIntegration:
    """Deeper checks on the SFT setup output."""

    @pytest.fixture()
    def setup_dir(self, tmp_path: Path) -> Path:
        return generate_setup(SFT_CONFIG, name="deep-sft", output_base=tmp_path)

    def test_frozen_config_sft_stage(self, setup_dir: Path):
        with open(setup_dir / "config.yaml") as f:
            data = yaml.safe_load(f)
        assert data["training"]["stage"] == 1  # Stage.SFT == 1

    def test_train_py_mentions_alpaca(self, setup_dir: Path):
        content = (setup_dir / "prepare.py").read_text()
        assert "tatsu-lab/alpaca" in content

    def test_train_py_no_reward_function_import(self, setup_dir: Path):
        """SFT should not import reward modules."""
        content = (setup_dir / "train.py").read_text()
        # The SFT template should not have "from rewards." imports
        assert "from rewards." not in content

    def test_no_rewards_directory(self, setup_dir: Path):
        assert not (setup_dir / "rewards").exists()
