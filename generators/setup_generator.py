"""Setup generator: creates self-contained setup_* directories from EnvelopeConfig.

This is the main orchestrator. It:
1. Loads and validates the config
2. Resolves technique and framework plugins
3. Checks compatibility
4. Renders Jinja2 templates into the output directory
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import jinja2

from envelope.config.loader import dump_config, load_config
from envelope.config.models import EnvelopeConfig
from envelope.config.validators import validate_config_or_raise
from envelope.frameworks.base import BaseFrameworkAdapter
from envelope.frameworks.capability_matrix import check_or_raise
from envelope.hardware.auto_optimizer import suggest_optimizations
from envelope.registry import discover_plugins, framework_registry, technique_registry
from envelope.techniques.base import BaseTechnique

TEMPLATES_DIR = Path(__file__).parent / "templates"


def inject_worker_middleware(output_dir: Path) -> None:
    """Copy envelope/middleware/ tree into output_dir/middleware/ for daemon coordination.

    Copies:
    - envelope/middleware/worker/ → setup_{name}/middleware/worker/
    - envelope/middleware/shared/ → setup_{name}/middleware/shared/
    - envelope/middleware/__init__.py → setup_{name}/middleware/__init__.py

    This makes the daemon available without manual setup.
    """
    middleware_src = Path(__file__).parent.parent / "middleware"
    middleware_dst = output_dir / "middleware"

    if middleware_src.exists():
        # Remove destination if it exists (idempotent)
        if middleware_dst.exists():
            shutil.rmtree(middleware_dst)
        # Copy entire middleware tree
        shutil.copytree(middleware_src, middleware_dst)
    else:
        raise FileNotFoundError(f"Source middleware not found: {middleware_src}")


def generate_setup(
    config_path: str | Path,
    name: str,
    output_base: str | Path = "setups",
    apply_suggestions: bool = False,
) -> Path:
    """Generate a self-contained setup directory from a YAML config.

    Args:
        config_path: Path to the YAML config
        name: Experiment name (used in folder name: setup_{name})
        output_base: Base directory for generated setups
        apply_suggestions: If True, auto-apply HW optimization suggestions

    Returns:
        Path to the generated setup directory
    """
    # Ensure plugins are discovered
    discover_plugins()

    # Load and validate
    config = load_config(config_path)
    validate_config_or_raise(config)

    # Resolve plugins
    technique_name = config.training.technique.value
    framework_name = config.framework.backend.value

    technique_cls = technique_registry.get(technique_name)
    technique: BaseTechnique = technique_cls()

    framework_cls = framework_registry.get(framework_name)
    framework: BaseFrameworkAdapter = framework_cls()

    # Check compatibility
    check_or_raise(technique_name, framework_name)

    # Technique-specific validation
    tech_errors = technique.validate_config(config)
    if tech_errors:
        raise ValueError(f"Technique validation errors:\n" + "\n".join(f"  - {e}" for e in tech_errors))

    # Framework-specific validation
    fw_errors = framework.validate_config(config)
    if fw_errors:
        raise ValueError(f"Framework validation errors:\n" + "\n".join(f"  - {e}" for e in fw_errors))

    # HW suggestions
    suggestions = suggest_optimizations(config)

    # Create output directory
    output_dir = Path(output_base) / f"setup_{name}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup Jinja2 environment
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined,
    )

    # Get template context
    context = framework.template_context(config)
    context["suggestions"] = suggestions
    context["technique_plugin"] = technique
    context["framework_plugin"] = framework

    # Render train.py
    template_file = framework.template_name(technique_name)
    _render_template(env, template_file, output_dir / "train.py", context)

    # Render prepare.py (data preparation module)
    _render_template(env, "prepare.py.j2", output_dir / "prepare.py", context)

    # Render run.sh
    launch_cmd = framework.launch_command(config)
    run_context = {**context, "launch_command": launch_cmd}
    _render_template(env, "run.sh.j2", output_dir / "run.sh", run_context)

    # Render requirements.txt
    requirements = framework.requirements(config)
    req_context = {"requirements": requirements}
    _render_template(env, "requirements.txt.j2", output_dir / "requirements.txt", req_context)

    # Save frozen config
    dump_config(config, output_dir / "config.yaml")

    # Copy reward functions if RL technique
    if technique.requires_reward and config.reward.functions:
        _copy_reward_modules(config, output_dir)

    # Copy framework-specific extra files (e.g., from_scratch lib)
    framework.extra_setup_files(config, output_dir)

    # Copy runtime diagnostics module (if enabled in config)
    if config.diagnostics.enabled and config.diagnostics.copy_runtime:
        _copy_diagnostics(output_dir)

    # Step 16: Inject worker middleware
    inject_worker_middleware(output_dir)

    # Make run.sh executable
    (output_dir / "run.sh").chmod(0o755)

    return output_dir


def _render_template(
    env: jinja2.Environment,
    template_name: str,
    output_path: Path,
    context: dict[str, Any],
) -> None:
    """Render a Jinja2 template to a file."""
    try:
        template = env.get_template(template_name)
    except jinja2.TemplateNotFound:
        # Fallback: generate a placeholder
        output_path.write_text(
            f"# Template '{template_name}' not yet implemented.\n"
            f"# This is a placeholder. Add the template to envelope/generators/templates/\n"
            f"raise NotImplementedError('Template {template_name} not found')\n"
        )
        return
    rendered = template.render(**context)
    output_path.write_text(rendered)


def _copy_reward_modules(config: EnvelopeConfig, output_dir: Path) -> None:
    """Copy reward function modules into the setup directory."""
    rewards_dir = output_dir / "rewards"
    rewards_dir.mkdir(exist_ok=True)
    (rewards_dir / "__init__.py").write_text("")
    for fn in config.reward.functions:
        module_parts = fn.module_path.split(".")
        # Try to find the source file
        source = Path(*module_parts).with_suffix(".py")
        if source.exists():
            shutil.copy2(source, rewards_dir / source.name)


def _copy_diagnostics(output_dir: Path) -> None:
    """Copy the runtime diagnostics module into the setup directory."""
    diagnostics_src = Path(__file__).parent.parent / "diagnostics" / "runtime.py"
    if diagnostics_src.exists():
        shutil.copy2(diagnostics_src, output_dir / "diagnostics.py")
