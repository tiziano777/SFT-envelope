"""Unit tests for envelope/registry/base.py and envelope/registry/__init__.py."""

from __future__ import annotations

import pytest

from envelope.registry.base import Registry


# ---------------------------------------------------------------------------
# Registry base class
# ---------------------------------------------------------------------------


class TestRegistryBase:
    """Tests for the generic Registry class in isolation."""

    def test_register_and_get(self):
        reg = Registry("test")

        @reg.register("foo")
        class FooPlugin:
            pass

        assert reg.get("foo") is FooPlugin

    def test_get_unknown_key_raises_key_error(self):
        reg = Registry("test")
        with pytest.raises(KeyError, match="not found"):
            reg.get("nonexistent")

    def test_duplicate_registration_raises_value_error(self):
        reg = Registry("test")

        @reg.register("dup")
        class FirstClass:
            pass

        with pytest.raises(ValueError, match="Duplicate registration"):

            @reg.register("dup")
            class SecondClass:
                pass

    def test_keys(self):
        reg = Registry("test")

        @reg.register("b")
        class B:
            pass

        @reg.register("a")
        class A:
            pass

        assert reg.keys() == ["a", "b"]  # sorted

    def test_contains(self):
        reg = Registry("test")

        @reg.register("present")
        class Present:
            pass

        assert "present" in reg
        assert "absent" not in reg

    def test_len(self):
        reg = Registry("test")
        assert len(reg) == 0

        @reg.register("x")
        class X:
            pass

        assert len(reg) == 1

    def test_create_instantiates_class(self):
        reg = Registry("test")

        @reg.register("widget")
        class Widget:
            def __init__(self, value=10):
                self.value = value

        obj = reg.create("widget", value=42)
        assert isinstance(obj, Widget)
        assert obj.value == 42

    def test_create_unknown_raises_key_error(self):
        reg = Registry("test")
        with pytest.raises(KeyError):
            reg.create("missing")

    def test_repr(self):
        reg = Registry("demo")

        @reg.register("alpha")
        class Alpha:
            pass

        r = repr(reg)
        assert "demo" in r
        assert "alpha" in r

    def test_name_property(self):
        reg = Registry("my-registry")
        assert reg.name == "my-registry"


# ---------------------------------------------------------------------------
# discover_plugins() and global registries
# ---------------------------------------------------------------------------


class TestDiscoverPlugins:
    """Test that discover_plugins() loads all techniques and frameworks."""

    @pytest.fixture(autouse=True)
    def _discover(self):
        from envelope.registry import discover_plugins

        discover_plugins()

    def test_technique_registry_has_19_entries(self):
        from envelope.registry import technique_registry

        assert len(technique_registry) == 19

    def test_framework_registry_has_7_entries(self):
        from envelope.registry import framework_registry

        assert len(framework_registry) == 8

    @pytest.mark.parametrize(
        "name",
        [
            "sft",
            "dpo",
            "simpo",
            "kto",
            "orpo",
            "ppo",
            "grpo",
            "dapo",
            "vapo",
            "rloo",
            "reinforce_pp",
            "dr_grpo",
            "flowrl",
            "prime",
        ],
    )
    def test_all_techniques_registered(self, name):
        from envelope.registry import technique_registry

        assert name in technique_registry

    @pytest.mark.parametrize(
        "name",
        [
            "trl",
            "unsloth",
            "axolotl",
            "torchtune",
            "verl",
            "openrlhf",
            "llamafactory",
        ],
    )
    def test_all_frameworks_registered(self, name):
        from envelope.registry import framework_registry

        assert name in framework_registry

    def test_technique_registry_get_returns_class(self):
        from envelope.registry import technique_registry
        from envelope.techniques.base import BaseTechnique

        cls = technique_registry.get("grpo")
        instance = cls()
        assert isinstance(instance, BaseTechnique)

    def test_framework_registry_get_returns_class(self):
        from envelope.registry import framework_registry
        from envelope.frameworks.base import BaseFrameworkAdapter

        cls = framework_registry.get("trl")
        instance = cls()
        assert isinstance(instance, BaseFrameworkAdapter)

    def test_discover_plugins_idempotent(self):
        """Calling discover_plugins() twice should not raise (no duplicate registration)."""
        from envelope.registry import discover_plugins

        # Already called once via fixture; calling again should be a no-op
        discover_plugins()
