"""Singleton registry instances for techniques and frameworks.

Import auto-discovers all plugins by importing the technique and framework packages.
"""

from __future__ import annotations

from envelope.registry.base import Registry

# These are used by plugins via @technique_registry.register("name")
technique_registry: Registry = Registry("technique")
framework_registry: Registry = Registry("framework")


def discover_plugins() -> None:
    """Import all plugin modules to trigger @register decorators."""
    # Techniques
    import envelope.techniques.sft  # noqa: F401
    import envelope.techniques.preference  # noqa: F401
    import envelope.techniques.rl  # noqa: F401
    import envelope.techniques.flow  # noqa: F401
    import envelope.techniques.distillation  # noqa: F401
    import envelope.techniques.reward  # noqa: F401
    # Frameworks
    import envelope.frameworks.single_node  # noqa: F401
    import envelope.frameworks.multi_node  # noqa: F401
    import envelope.frameworks.from_scratch  # noqa: F401


__all__ = ["technique_registry", "framework_registry", "discover_plugins"]
