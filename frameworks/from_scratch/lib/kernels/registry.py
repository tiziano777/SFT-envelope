"""Kernel registry: auto-dispatch between Triton and PyTorch implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


def _triton_available() -> bool:
    try:
        import triton  # noqa: F401
        return True
    except ImportError:
        return False


class TritonOp(ABC):
    """Base class for operations with Triton + PyTorch fallback.

    Subclass this and implement both forward_triton() and forward_torch().
    The __call__ method automatically dispatches based on Triton availability.
    """

    @abstractmethod
    def forward_triton(self, *args: Any, **kwargs: Any) -> Any:
        """Triton kernel implementation (fast path)."""

    @abstractmethod
    def forward_torch(self, *args: Any, **kwargs: Any) -> Any:
        """PyTorch fallback implementation (guaranteed to work)."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if _triton_available():
            return self.forward_triton(*args, **kwargs)
        return self.forward_torch(*args, **kwargs)


class KernelRegistry:
    """Registry mapping kernel names to TritonOp instances.

    Provides a single lookup point for all custom kernel operations.
    """

    def __init__(self) -> None:
        self._ops: dict[str, TritonOp] = {}

    def register(self, name: str) -> Callable[[type[TritonOp]], type[TritonOp]]:
        """Decorator to register a TritonOp subclass."""
        def decorator(cls: type[TritonOp]) -> type[TritonOp]:
            self._ops[name] = cls()
            return cls
        return decorator

    def get(self, name: str) -> TritonOp:
        """Get a registered kernel op by name. Raises KeyError if not found."""
        if name not in self._ops:
            available = sorted(self._ops.keys())
            raise KeyError(f"Kernel '{name}' not found. Available: {available}")
        return self._ops[name]

    def keys(self) -> list[str]:
        return sorted(self._ops.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._ops
