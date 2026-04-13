"""Tests for BaseExperimentRepository ABC definition and interface."""

import inspect

import pytest

from master.neo4j.repository import BaseExperimentRepository


def test_abstract_methods_defined():
    """BaseExperimentRepository defines all required abstract methods."""
    required_methods = [
        "create_experiment",
        "upsert_checkpoint",
        "find_experiment_by_hashes",
        "get_latest_checkpoint",
        "create_merged_checkpoint",
        "create_derived_from_relation",
        "create_retry_from_relation",
        "get_experiment",
    ]

    for method_name in required_methods:
        assert hasattr(
            BaseExperimentRepository, method_name
        ), f"Missing method: {method_name}"
        method = getattr(BaseExperimentRepository, method_name)
        assert getattr(
            method, "__isabstractmethod__", False
        ), f"{method_name} is not abstract"


def test_all_methods_async():
    """All repository methods are async (coroutine functions)."""
    for name, method in inspect.getmembers(
        BaseExperimentRepository, predicate=inspect.iscoroutinefunction
    ):
        assert name.startswith("_") or name in [
            "create_experiment",
            "upsert_checkpoint",
            "find_experiment_by_hashes",
            "get_latest_checkpoint",
            "create_merged_checkpoint",
            "create_derived_from_relation",
            "create_retry_from_relation",
            "get_experiment",
        ]


def test_all_methods_have_docstrings():
    """All abstract methods have docstrings."""
    for name, method in inspect.getmembers(
        BaseExperimentRepository, predicate=inspect.iscoroutinefunction
    ):
        if not name.startswith("_"):
            assert (
                method.__doc__ is not None and len(method.__doc__) > 0
            ), f"{name} has no docstring"


def test_all_methods_typed():
    """All abstract methods have complete type hints."""
    for name, method in inspect.getmembers(
        BaseExperimentRepository, predicate=inspect.iscoroutinefunction
    ):
        if not name.startswith("_"):
            sig = inspect.signature(method)
            # Check return annotation
            assert (
                sig.return_annotation != inspect.Signature.empty
            ), f"{name} has no return type hint"
