"""Shared test fixtures for Shuttle."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_shuttle_dir(tmp_path):
    """Temporary ~/.shuttle/ directory for tests."""
    shuttle_dir = tmp_path / ".shuttle"
    shuttle_dir.mkdir()
    return shuttle_dir
