"""Shuttle database package — models, engine, session utilities, and repositories."""

from shuttle.db.engine import create_db_engine, create_session_factory, init_db
from shuttle.db.models import (
    AppConfig,
    Base,
    CommandLog,
    Node,
    SecurityRule,
    Session,
)
from shuttle.db.repository import (
    ConfigRepo,
    LogRepo,
    NodeRepo,
    RuleRepo,
    SessionRepo,
)

__all__ = [
    # Models
    "Base",
    "Node",
    "SecurityRule",
    "Session",
    "CommandLog",
    "AppConfig",
    # Engine helpers
    "create_db_engine",
    "create_session_factory",
    "init_db",
    # Repositories
    "NodeRepo",
    "RuleRepo",
    "SessionRepo",
    "LogRepo",
    "ConfigRepo",
]
