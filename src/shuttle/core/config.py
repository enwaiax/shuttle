"""Shuttle configuration via pydantic-settings (env-var driven)."""

from pathlib import Path

from pydantic_settings import BaseSettings


class ShuttleConfig(BaseSettings):
    """Top-level configuration for the Shuttle SSH gateway.

    All fields can be overridden with environment variables prefixed SHUTTLE_.
    For example: SHUTTLE_WEB_PORT=9000.
    """

    model_config = {"env_prefix": "SHUTTLE_"}

    # Core paths / database
    shuttle_dir: Path = Path.home() / ".shuttle"
    db_url: str = "sqlite+aiosqlite:///~/.shuttle/shuttle.db"

    # Web server
    web_host: str = "127.0.0.1"
    web_port: int = 8000

    # Connection pool settings
    pool_max_total: int = 50
    pool_max_per_node: int = 5
    pool_idle_timeout: int = 300
    pool_max_lifetime: int = 3600
    pool_queue_size: int = 10
