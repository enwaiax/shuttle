"""Tests for python -m shuttle entrypoint."""

from __future__ import annotations

import runpy
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import shuttle


def test_dunder_main_invokes_cli_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """__main__ should call the Typer app once (same as `python -m shuttle`)."""
    mock_app = MagicMock()
    monkeypatch.setattr("shuttle.cli.app", mock_app)
    main_path = Path(shuttle.__file__).resolve().parent / "__main__.py"
    runpy.run_path(str(main_path), run_name="__main__")
    mock_app.assert_called_once()
