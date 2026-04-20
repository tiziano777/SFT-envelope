"""CLI entry point for FineTuning-Envelope."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """FineTuning-Envelope: Two-level envelope for LLM fine-tuning experiments."""


@main.command()
@click.option("--name", "-n", required=True, help="Experiment name (used in folder: setup_{name})")
@click.option("--config", "-c", required=True, type=click.Path(exists=True), help="Path to YAML config")
@click.option("--output", "-o", default="setups", help="Base output directory")
@click.option("--apply-suggestions", is_flag=True, help="Auto-apply HW optimization suggestions")
def setup(name: str, config: str, output: str, apply_suggestions: bool):
    """Generate a self-contained setup directory from a YAML config."""
    from envelope.generators.setup_generator import generate_setup

    console.print(f"[bold blue]Generating setup: setup_{name}[/]")
    console.print(f"  Config: {config}")

    try:
        output_dir = generate_setup(config, name, output, apply_suggestions)
        console.print(f"\n[bold green]Setup generated successfully![/]")
        console.print(f"  Output: {output_dir}")
        console.print(f"\n  To run: [cyan]bash {output_dir}/run.sh[/]")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/] {e}")
        raise SystemExit(1)


@main.command()
@click.option("--config", "-c", required=True, type=click.Path(exists=True), help="Path to YAML config")
def validate(config: str):
    """Validate a YAML configuration without generating files."""
    from envelope.config.loader import load_config
    from envelope.config.validators import validate_config
    from envelope.hardware.auto_optimizer import suggest_optimizations
    from envelope.registry import discover_plugins

    discover_plugins()
    console.print(f"[bold blue]Validating: {config}[/]")

    try:
        cfg = load_config(config)
        errors = validate_config(cfg)
        if errors:
            console.print("\n[bold yellow]Validation warnings:[/]")
            for err in errors:
                console.print(f"  [yellow]- {err}[/]")
        else:
            console.print("\n[bold green]Config is valid![/]")

        # Show suggestions
        suggestions = suggest_optimizations(cfg)
        if suggestions:
            console.print("\n[bold cyan]Hardware optimization suggestions:[/]")
            for key, val in suggestions.items():
                if not key.startswith("_"):
                    reason = suggestions.get(f"_reason_{key.split('.')[-1]}", "")
                    console.print(f"  {key} = {val}")
                    if reason:
                        console.print(f"    [dim]{reason}[/]")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/] {e}")
        raise SystemExit(1)


@main.command()
def techniques():
    """List all registered training techniques."""
    from envelope.registry import discover_plugins, technique_registry

    discover_plugins()

    table = Table(title="Registered Techniques")
    table.add_column("Key", style="cyan")
    table.add_column("Class", style="green")

    for key in technique_registry.keys():
        cls = technique_registry.get(key)
        table.add_row(key, cls.__name__)

    console.print(table)


@main.command()
def frameworks():
    """List all registered framework adapters."""
    from envelope.registry import discover_plugins, framework_registry

    discover_plugins()

    table = Table(title="Registered Frameworks")
    table.add_column("Key", style="cyan")
    table.add_column("Class", style="green")

    for key in framework_registry.keys():
        cls = framework_registry.get(key)
        table.add_row(key, cls.__name__)

    console.print(table)


@main.command()
@click.argument("technique")
def compatible(technique: str):
    """Show compatible frameworks for a technique."""
    from envelope.frameworks.capability_matrix import get_compatible_frameworks

    fws = get_compatible_frameworks(technique)
    if fws:
        console.print(f"[bold]Compatible frameworks for '{technique}':[/]")
        for fw in fws:
            console.print(f"  [green]- {fw}[/]")
    else:
        console.print(f"[bold red]No compatible frameworks found for '{technique}'[/]")


if __name__ == "__main__":
    main()
