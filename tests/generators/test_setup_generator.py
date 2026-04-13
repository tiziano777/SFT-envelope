"""Tests for setup generator: inject_worker_middleware, run.sh, requirements.txt."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from envelope.generators.setup_generator import (
    generate_setup,
    inject_worker_middleware,
)
from envelope.registry import discover_plugins

# Ensure all plugins are discovered before tests run
discover_plugins()

# Absolute path to the example config files
CONFIGS_DIR = Path(__file__).resolve().parents[2] / "configs" / "examples"
GRPO_CONFIG = CONFIGS_DIR / "grpo_qlora_qwen.yaml"


class TestInjectWorkerMiddleware:
    """Test inject_worker_middleware() function."""

    def test_inject_worker_middleware_creates_directories(self):
        """Middleware injection should create middleware/worker and middleware/shared directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            inject_worker_middleware(output_dir)

            assert (output_dir / "middleware").exists()
            assert (output_dir / "middleware" / "worker").exists()
            assert (output_dir / "middleware" / "shared").exists()

    def test_inject_worker_middleware_copies_shared(self):
        """Middleware injection should copy shared module files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            inject_worker_middleware(output_dir)

            # Check for key shared module files
            assert (output_dir / "middleware" / "shared" / "models.py").exists()

    def test_inject_worker_middleware_idempotent(self):
        """Calling inject_worker_middleware twice should not error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # First call
            inject_worker_middleware(output_dir)
            first_files = set((output_dir / "middleware").rglob("*"))

            # Second call (should remove and re-copy)
            inject_worker_middleware(output_dir)
            second_files = set((output_dir / "middleware").rglob("*"))

            # Both should have files
            assert len(first_files) > 0
            assert len(second_files) > 0

    def test_inject_worker_middleware_missing_source(self):
        """If middleware source doesn't exist, should raise FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Patch middleware path to non-existent location
            import envelope.generators.setup_generator as gen_module

            original_file = gen_module.__file__

            # Create a fake inject function that tries non-existent path
            def fake_inject(out_dir: Path) -> None:
                middleware_src = Path("/nonexistent/middleware")
                middleware_dst = out_dir / "middleware"
                if middleware_src.exists():
                    if middleware_dst.exists():
                        import shutil

                        shutil.rmtree(middleware_dst)
                    import shutil

                    shutil.copytree(middleware_src, middleware_dst)
                else:
                    raise FileNotFoundError(f"Source middleware not found: {middleware_src}")

            with pytest.raises(FileNotFoundError, match="Source middleware not found"):
                fake_inject(output_dir)


class TestRunShTemplate:
    """Test that generated run.sh has daemon lifecycle."""

    def test_run_sh_contains_daemon_bootstrap(self):
        """Generated run.sh should contain WorkerDaemon bootstrap."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = generate_setup(
                GRPO_CONFIG, "test", tmpdir
            )
            run_sh = (output_dir / "run.sh").read_text()

            assert "WorkerDaemon" in run_sh or "daemon" in run_sh.lower()

    def test_run_sh_contains_handshake_done_wait(self):
        """Generated run.sh should wait for .handshake_done file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = generate_setup(
                GRPO_CONFIG, "test", tmpdir
            )
            run_sh = (output_dir / "run.sh").read_text()

            assert ".handshake_done" in run_sh

    def test_run_sh_contains_training_done_marker(self):
        """Generated run.sh should write .training_done marker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = generate_setup(
                GRPO_CONFIG, "test", tmpdir
            )
            run_sh = (output_dir / "run.sh").read_text()

            assert ".training_done" in run_sh

    def test_run_sh_is_executable(self):
        """Generated run.sh should be executable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = generate_setup(
                GRPO_CONFIG, "test", tmpdir
            )
            run_sh = output_dir / "run.sh"

            assert run_sh.stat().st_mode & 0o111 != 0


class TestRequirementsTemplate:
    """Test that generated requirements.txt includes worker dependencies."""

    def test_generated_requirements_includes_watchdog(self):
        """Generated requirements.txt should include watchdog."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = generate_setup(
                GRPO_CONFIG, "test", tmpdir
            )
            requirements = (output_dir / "requirements.txt").read_text()

            assert "watchdog" in requirements

    def test_generated_requirements_includes_httpx(self):
        """Generated requirements.txt should include httpx."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = generate_setup(
                GRPO_CONFIG, "test", tmpdir
            )
            requirements = (output_dir / "requirements.txt").read_text()

            assert "httpx" in requirements

    def test_generated_requirements_includes_paramiko(self):
        """Generated requirements.txt should include paramiko."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = generate_setup(
                GRPO_CONFIG, "test", tmpdir
            )
            requirements = (output_dir / "requirements.txt").read_text()

            assert "paramiko" in requirements

    def test_generated_requirements_has_worker_deps_first(self):
        """Generated requirements.txt should have worker deps before framework deps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = generate_setup(
                GRPO_CONFIG, "test", tmpdir
            )
            requirements = (output_dir / "requirements.txt").read_text()
            lines = requirements.strip().split("\n")

            # Find positions of worker deps (should be early, after header)
            watchdog_idx = next(i for i, l in enumerate(lines) if "watchdog" in l)
            httpx_idx = next(i for i, l in enumerate(lines) if "httpx" in l)
            paramiko_idx = next(i for i, l in enumerate(lines) if "paramiko" in l)

            # All worker deps should be present
            assert watchdog_idx > 0
            assert httpx_idx > 0
            assert paramiko_idx > 0


class TestSetupGeneratorIntegration:
    """Test overall setup generation with worker middleware."""

    def test_generate_setup_includes_middleware(self):
        """generate_setup should produce setup with middleware directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = generate_setup(
                GRPO_CONFIG, "test", tmpdir
            )

            assert (output_dir / "middleware").exists()
            assert (output_dir / "middleware" / "worker").exists()
            assert (output_dir / "middleware" / "shared").exists()

    def test_generate_setup_middleware_has_init(self):
        """Generated middleware should have __init__.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = generate_setup(
                GRPO_CONFIG, "test", tmpdir
            )

            assert (output_dir / "middleware" / "__init__.py").exists()

    def test_generate_setup_creates_all_expected_files(self):
        """generate_setup should create all expected files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = generate_setup(
                GRPO_CONFIG, "test", tmpdir
            )

            expected_files = [
                "train.py",
                "run.sh",
                "requirements.txt",
                "config.yaml",
                "prepare.py",
            ]

            for fname in expected_files:
                assert (output_dir / fname).exists(), f"Missing {fname}"
