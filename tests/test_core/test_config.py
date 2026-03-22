"""Tests for ShuttleConfig pydantic-settings configuration."""

from pathlib import Path

from shuttle.core.config import ShuttleConfig


def test_default_config():
    """ShuttleConfig should provide sensible defaults without any env vars set."""
    cfg = ShuttleConfig()

    assert cfg.shuttle_dir == Path.home() / ".shuttle"
    assert cfg.db_url == "sqlite+aiosqlite:///~/.shuttle/shuttle.db"
    assert cfg.web_host == "127.0.0.1"
    assert cfg.web_port == 9876
    assert cfg.pool_max_total == 50
    assert cfg.pool_max_per_node == 5
    assert cfg.pool_idle_timeout == 300
    assert cfg.pool_max_lifetime == 3600
    assert cfg.pool_queue_size == 10


def test_config_custom_values(monkeypatch, tmp_path):
    """Env vars with the SHUTTLE_ prefix should override defaults."""
    shuttle_dir = tmp_path / ".shuttle"
    monkeypatch.setenv("SHUTTLE_SHUTTLE_DIR", str(shuttle_dir))
    monkeypatch.setenv("SHUTTLE_DB_URL", "sqlite+aiosqlite:///custom.db")
    monkeypatch.setenv("SHUTTLE_WEB_HOST", "0.0.0.0")
    monkeypatch.setenv("SHUTTLE_WEB_PORT", "9090")
    monkeypatch.setenv("SHUTTLE_POOL_MAX_TOTAL", "100")
    monkeypatch.setenv("SHUTTLE_POOL_MAX_PER_NODE", "10")
    monkeypatch.setenv("SHUTTLE_POOL_IDLE_TIMEOUT", "600")
    monkeypatch.setenv("SHUTTLE_POOL_MAX_LIFETIME", "7200")
    monkeypatch.setenv("SHUTTLE_POOL_QUEUE_SIZE", "20")

    cfg = ShuttleConfig()

    assert cfg.shuttle_dir == shuttle_dir
    assert cfg.db_url == "sqlite+aiosqlite:///custom.db"
    assert cfg.web_host == "0.0.0.0"
    assert cfg.web_port == 9090
    assert cfg.pool_max_total == 100
    assert cfg.pool_max_per_node == 10
    assert cfg.pool_idle_timeout == 600
    assert cfg.pool_max_lifetime == 7200
    assert cfg.pool_queue_size == 20
