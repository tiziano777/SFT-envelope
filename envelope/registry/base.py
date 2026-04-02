"""Generic Registry class for the plugin architecture.

Techniques and frameworks register themselves via decorators.
The registry supports auto-discovery and provides type-safe lookup.
"""

from __future__ import annotations

from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """A generic registry that maps string names to plugin instances/classes."""

    def __init__(self, name: str):
        self._name = name
        self._entries: dict[str, type[T]] = {}

    @property
    def name(self) -> str:
        return self._name

    def register(self, key: str) -> Callable[[type[T]], type[T]]:
        """Decorator to register a class under the given key.

        Usage:
            @technique_registry.register("grpo")
            class GRPOTechnique(BaseTechnique):
                ...
        """

        def decorator(cls: type[T]) -> type[T]:
            if key in self._entries:
                raise ValueError(
                    f"Duplicate registration in {self._name}: '{key}' is already registered "
                    f"to {self._entries[key].__name__}. Cannot register {cls.__name__}."
                )
            self._entries[key] = cls
            return cls

        return decorator

    def get(self, key: str) -> type[T]:
        """Retrieve a registered class by key. Raises KeyError if not found."""
        if key not in self._entries:
            available = ", ".join(sorted(self._entries.keys()))
            raise KeyError(
                f"'{key}' not found in {self._name} registry. Available: [{available}]"
            )
        return self._entries[key]

    def create(self, key: str, **kwargs) -> T:
        """Instantiate a registered class by key."""
        cls = self.get(key)
        return cls(**kwargs)

    def keys(self) -> list[str]:
        """Return all registered keys."""
        return sorted(self._entries.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"Registry(name={self._name!r}, entries={self.keys()})"
