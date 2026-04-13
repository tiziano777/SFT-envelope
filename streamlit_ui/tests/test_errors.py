"""Tests for error classes."""

from __future__ import annotations

import pytest

from streamlit_ui.errors import APIError, DeleteProtectionError, UIError, ValidationError


def test_ui_error_user_message():
    """Test UIError user message."""
    error = UIError("User message", "Technical details")
    assert str(error) == "User message"
    assert error.user_message == "User message"
    assert error.details == "Technical details"


def test_validation_error():
    """Test ValidationError."""
    error = ValidationError("model_name", "required field", "Extra details")
    assert "model_name" in str(error)
    assert "required field" in str(error)


def test_api_error():
    """Test APIError."""
    error = APIError(404, "Not Found", "Resource missing")
    assert "404" in str(error)
    assert error.status_code == 404


def test_delete_protection_error():
    """Test DeleteProtectionError."""
    error = DeleteProtectionError("model", 3, "experiment")
    assert "Cannot delete" in str(error)
    assert "3" in str(error)
    assert error.dependency_count == 3
