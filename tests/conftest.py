"""Pytest configuration for InkGen tests."""

from __future__ import annotations


def pytest_configure(config) -> None:
    """Register project condition markers used for traceability."""
    config.addinivalue_line("markers", "condition(*ids): map tests to design or implementation conditions")
