"""End-to-end tests for setup_generator scaffold generation."""

import shutil
from pathlib import Path

import pytest

from envelope.generators.setup_generator import generate_setup


@pytest.fixture
def temp_setups_dir(tmp_path):
    """Provide a temporary setups directory for test output."""
    setups_dir = tmp_path / "setups"
    setups_dir.mkdir()
    yield setups_dir
    # Cleanup (tmp_path is auto-cleaned by pytest)


@pytest.mark.parametrize("config_file,technique,name", [
    ("configs/examples/sft_baseline.yaml", "sft", "sft-test"),
    ("configs/examples/grpo_qlora_qwen.yaml", "grpo", "grpo-test"),
])
def test_generate_setup(config_file, technique, name, temp_setups_dir):
    """Test scaffold generation for different techniques and frameworks."""
    config_path = Path(config_file)

    # Skip if config doesn't exist
    if not config_path.exists():
        pytest.skip(f"Config file not found: {config_path}")

    # Generate the setup
    output_dir = generate_setup(
        config_path=config_path,
        name=name,
        output_base=str(temp_setups_dir),
    )

    # Verify output directory exists
    assert output_dir.exists(), f"Output directory not created: {output_dir}"
    assert output_dir.is_dir(), f"Output path is not a directory: {output_dir}"

    # Check for required files
    required_files = ["train.py", "prepare.py", "config.yaml", "requirements.txt"]
    for filename in required_files:
        file_path = output_dir / filename
        assert file_path.exists(), f"Missing required file: {filename} in {output_dir}"
        assert file_path.stat().st_size > 0, f"File is empty: {filename}"

    # Verify config.yaml is valid YAML
    import yaml
    config_yaml = output_dir / "config.yaml"
    with open(config_yaml) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "config.yaml is not a valid YAML dict"

    # Verify Python files are syntactically valid
    for py_file in ["train.py", "prepare.py"]:
        py_path = output_dir / py_file
        with open(py_path) as f:
            code = f.read()
        # Basic check: should be compilable
        try:
            compile(code, str(py_path), "exec")
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {py_file}: {e}")
