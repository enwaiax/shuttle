# Shuttle Backend Core — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete Shuttle backend — from project scaffold through working MCP tools and CLI — so that `uvx shuttle` starts a functional SSH MCP server with connection pooling, session isolation, and 4-level command security.

**Architecture:** Dual-process model (this plan covers the MCP process only). Core engine shared by MCP and future Web process. SQLAlchemy ORM with SQLite (WAL mode). AsyncSSH for SSH connections. FastMCP for MCP protocol.

**Tech Stack:** Python 3.12+, FastMCP 2.0+, AsyncSSH, SQLAlchemy 2.0 (async), aiosqlite, Pydantic 2.0, Typer, cryptography, loguru

**Spec:** `docs/superpowers/specs/2026-03-20-shuttle-design.md`

**Scope:** This is Plan 1 of 2. Plan 2 (Web Panel) will be written after this plan is complete.

---

## File Structure

```
src/
└── shuttle/
    ├── __init__.py              # Package init, version
    ├── __main__.py              # python -m shuttle entry
    ├── cli.py                   # Typer CLI (shuttle, shuttle web, shuttle node, shuttle config)
    ├── core/
    │   ├── __init__.py          # Re-exports
    │   ├── config.py            # ShuttleConfig (Pydantic Settings), data dir management
    │   ├── credentials.py       # Fernet encrypt/decrypt, keyfile management
    │   ├── connection_pool.py   # ConnectionPool, PooledConnection
    │   ├── proxy.py             # connect_with_proxy (Jump Host)
    │   ├── security.py          # CommandGuard, SecurityLevel, SecurityDecision, ConfirmTokenStore
    │   └── session.py           # SSHSession, SessionManager, CommandResult
    ├── db/
    │   ├── __init__.py          # Re-exports
    │   ├── engine.py            # create_db_engine, init_db
    │   ├── models.py            # Node, SecurityRule, Session, CommandLog, AppConfig
    │   ├── repository.py        # NodeRepo, RuleRepo, SessionRepo, LogRepo, ConfigRepo
    │   └── seeds.py             # Default security rule seeds
    └── mcp/
        ├── __init__.py          # Re-exports
        ├── server.py            # create_mcp_server, MCP startup orchestration
        └── tools.py             # ssh_execute, ssh_upload, ssh_download, ssh_list_nodes, ssh_session_*
tests/
├── conftest.py                  # Shared fixtures (tmp DB, mock SSH)
├── test_core/
│   ├── test_config.py
│   ├── test_credentials.py
│   ├── test_connection_pool.py
│   ├── test_security.py
│   └── test_session.py
├── test_db/
│   ├── test_models.py
│   └── test_repository.py
└── test_mcp/
    ├── test_tools.py
    ├── test_server.py
    └── test_integration.py
pyproject.toml                   # shuttle-mcp package config
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/shuttle/__init__.py`
- Create: `src/shuttle/__main__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Remove old source and create new project structure**

```bash
# Remove old source (we're doing a full rewrite)
rm -rf src/ssh_mcp
# Create new directory structure
mkdir -p src/shuttle/core src/shuttle/db src/shuttle/mcp src/shuttle/web/routes src/shuttle/web/static
mkdir -p tests/test_core tests/test_db tests/test_mcp
```

- [ ] **Step 2: Write pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "shuttle-mcp"
version = "0.1.0"
description = "Secure SSH gateway for AI assistants — MCP server with connection pooling, session isolation, and command safety"
authors = [{ name = "enwaiax", email = "enwaiax@users.noreply.github.com" }]
readme = "README.md"
license = { text = "ISC" }
requires-python = ">=3.12"
keywords = ["ssh", "mcp", "ai", "llm", "remote", "shuttle"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3.12",
    "Topic :: System :: Networking",
]

dependencies = [
    "fastmcp>=2.0.0",
    "asyncssh>=2.14.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "aiosqlite>=0.19.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "typer>=0.12.0",
    "cryptography>=41.0.0",
    "loguru>=0.7.0",
    "uvicorn>=0.27.0",
    "fastapi>=0.110.0",
]

[project.scripts]
shuttle = "shuttle.cli:app"

[project.urls]
homepage = "https://github.com/enwaiax/shuttle"
repository = "https://github.com/enwaiax/shuttle"

[tool.hatch.build.targets.wheel]
packages = ["src/shuttle"]

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers"
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py312"
line-length = 88

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=1.0.0",
    "pytest-cov>=6.0.0",
    "pytest-mock>=3.14.0",
    "ruff>=0.4.0",
]
```

- [ ] **Step 3: Write src/shuttle/__init__.py**

```python
"""Shuttle — Secure SSH gateway for AI assistants."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Write src/shuttle/__main__.py**

```python
"""Allow running as python -m shuttle."""

from shuttle.cli import app

app()
```

- [ ] **Step 5: Write initial tests/conftest.py**

Note: Only include `tmp_shuttle_dir` fixture here. The `db_engine` and `db_session` fixtures are added in Task 2 after `models.py` exists, to avoid import errors.

```python
"""Shared test fixtures for Shuttle."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_shuttle_dir(tmp_path):
    """Temporary ~/.shuttle/ directory for tests."""
    shuttle_dir = tmp_path / ".shuttle"
    shuttle_dir.mkdir()
    return shuttle_dir
```

- [ ] **Step 6: Create empty __init__.py files for all subpackages**

Create these files with empty content (or a single docstring):
- `src/shuttle/core/__init__.py`
- `src/shuttle/db/__init__.py`
- `src/shuttle/mcp/__init__.py`
- `src/shuttle/web/__init__.py`
- `src/shuttle/web/routes/__init__.py`
- `tests/test_core/__init__.py`
- `tests/test_db/__init__.py`
- `tests/test_mcp/__init__.py`

- [ ] **Step 7: Verify project installs and pytest runs**

```bash
uv sync
uv run pytest --co -q
```

Expected: 0 tests collected, no import errors.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: scaffold Shuttle project structure

Replace fastmcp-ssh-server with shuttle-mcp package.
New directory layout: core/, db/, mcp/, web/."
```

---

### Task 2: Database Models

**Files:**
- Create: `src/shuttle/db/models.py`
- Create: `tests/test_db/test_models.py`
- Modify: `tests/conftest.py` (add db_engine and db_session fixtures)

- [ ] **Step 0: Add DB fixtures to conftest.py**

Append to `tests/conftest.py`:

```python
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from shuttle.db.models import Base


@pytest_asyncio.fixture
async def db_engine(tmp_path):
    """In-memory async SQLAlchemy engine for tests."""
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Async SQLAlchemy session for tests."""
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
```

- [ ] **Step 1: Write the test**

```python
"""Tests for Shuttle ORM models."""

import pytest
from sqlalchemy import select

from shuttle.db.models import (
    AppConfig,
    Base,
    CommandLog,
    Node,
    SecurityRule,
    Session,
)


@pytest.mark.asyncio
async def test_create_node(db_session):
    node = Node(
        name="dev-server",
        host="192.168.1.1",
        port=22,
        username="root",
        auth_type="password",
        encrypted_credential="encrypted-value",
    )
    db_session.add(node)
    await db_session.commit()

    result = await db_session.execute(select(Node).where(Node.name == "dev-server"))
    fetched = result.scalar_one()
    assert fetched.host == "192.168.1.1"
    assert fetched.port == 22
    assert fetched.status == "unknown"
    assert fetched.id is not None


@pytest.mark.asyncio
async def test_node_jump_host_fk(db_session):
    bastion = Node(
        name="bastion",
        host="10.0.0.1",
        port=22,
        username="jump",
        auth_type="key",
        encrypted_credential="key-data",
    )
    db_session.add(bastion)
    await db_session.flush()

    target = Node(
        name="target",
        host="10.0.0.2",
        port=22,
        username="app",
        auth_type="password",
        encrypted_credential="pass",
        jump_host_id=bastion.id,
    )
    db_session.add(target)
    await db_session.commit()

    result = await db_session.execute(select(Node).where(Node.name == "target"))
    fetched = result.scalar_one()
    assert fetched.jump_host_id == bastion.id


@pytest.mark.asyncio
async def test_create_security_rule(db_session):
    rule = SecurityRule(
        pattern=r"sudo .*",
        level="confirm",
        description="Require confirmation for sudo commands",
        priority=10,
    )
    db_session.add(rule)
    await db_session.commit()

    result = await db_session.execute(select(SecurityRule))
    fetched = result.scalar_one()
    assert fetched.level == "confirm"
    assert fetched.enabled is True
    assert fetched.node_id is None  # Global rule


@pytest.mark.asyncio
async def test_create_session(db_session):
    node = Node(
        name="test",
        host="1.2.3.4",
        port=22,
        username="u",
        auth_type="password",
        encrypted_credential="p",
    )
    db_session.add(node)
    await db_session.flush()

    session = Session(
        node_id=node.id,
        working_directory="/home/u",
        status="active",
    )
    db_session.add(session)
    await db_session.commit()

    result = await db_session.execute(select(Session))
    fetched = result.scalar_one()
    assert fetched.status == "active"
    assert fetched.closed_at is None


@pytest.mark.asyncio
async def test_create_command_log(db_session):
    node = Node(
        name="n", host="h", port=22, username="u",
        auth_type="password", encrypted_credential="p",
    )
    db_session.add(node)
    await db_session.flush()

    session = Session(
        node_id=node.id, working_directory="/", status="active",
    )
    db_session.add(session)
    await db_session.flush()

    log = CommandLog(
        session_id=session.id,
        node_id=node.id,
        command="ls -la",
        exit_code=0,
        stdout="total 0",
        stderr="",
        security_level="allow",
        duration_ms=42,
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(select(CommandLog))
    fetched = result.scalar_one()
    assert fetched.command == "ls -la"
    assert fetched.bypassed is False


@pytest.mark.asyncio
async def test_command_log_nullable_session(db_session):
    """CommandLog.session_id can be None for stateless execution."""
    node = Node(
        name="n2", host="h", port=22, username="u",
        auth_type="password", encrypted_credential="p",
    )
    db_session.add(node)
    await db_session.flush()

    log = CommandLog(
        session_id=None,
        node_id=node.id,
        command="whoami",
        exit_code=0,
        stdout="root",
        stderr="",
        security_level="allow",
        duration_ms=5,
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(select(CommandLog).where(CommandLog.command == "whoami"))
    fetched = result.scalar_one()
    assert fetched.session_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db/test_models.py -v`
Expected: FAIL (ImportError — models.py doesn't exist yet)

- [ ] **Step 3: Write src/shuttle/db/models.py**

```python
"""Shuttle ORM models — SQLAlchemy 2.0 declarative style."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=22)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "password" | "key"
    encrypted_credential: Mapped[str] = mapped_column(Text, nullable=False)
    jump_host_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
    )
    tags: Mapped[dict | list | None] = mapped_column(JSON, default=list)
    pool_config: Mapped[dict | None] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class SecurityRule(Base):
    __tablename__ = "security_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # block/confirm/warn/allow
    node_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False
    )
    working_directory: Mapped[str] = mapped_column(Text, default="/")
    env_vars: Mapped[dict | None] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommandLog(Base):
    __tablename__ = "command_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True
    )
    node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False
    )
    command: Mapped[str] = mapped_column(Text, nullable=False)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    security_level: Mapped[str] = mapped_column(String(20), default="allow")
    security_rule_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    bypassed: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AppConfig(Base):
    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[dict | list | str | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_db/test_models.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/shuttle/db/models.py tests/test_db/test_models.py
git commit -m "feat: add SQLAlchemy ORM models (Node, SecurityRule, Session, CommandLog, AppConfig)"
```

---

### Task 3: Database Engine & Init

**Files:**
- Create: `src/shuttle/db/engine.py`
- Modify: `src/shuttle/db/__init__.py`

- [ ] **Step 1: Write src/shuttle/db/engine.py**

```python
"""Database engine creation and initialization."""

from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

DEFAULT_SHUTTLE_DIR = Path.home() / ".shuttle"
DEFAULT_DB_PATH = DEFAULT_SHUTTLE_DIR / "shuttle.db"


def create_db_engine(url: str | None = None):
    """Create async SQLAlchemy engine.

    Default: SQLite at ~/.shuttle/shuttle.db
    Configurable: postgresql+asyncpg://, mysql+aiomysql://, etc.
    """
    if url is None:
        DEFAULT_SHUTTLE_DIR.mkdir(parents=True, exist_ok=True)
        url = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"

    engine = create_async_engine(url, echo=False)

    if "sqlite" in url:
        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragma(conn, _):
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


def create_session_factory(engine) -> sessionmaker:
    """Create async session factory."""
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db(engine) -> None:
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2: Update src/shuttle/db/__init__.py**

```python
"""Shuttle database layer."""

from .engine import create_db_engine, create_session_factory, init_db
from .models import AppConfig, Base, CommandLog, Node, SecurityRule, Session

__all__ = [
    "create_db_engine",
    "create_session_factory",
    "init_db",
    "Base",
    "Node",
    "SecurityRule",
    "Session",
    "CommandLog",
    "AppConfig",
]
```

- [ ] **Step 3: Verify existing tests still pass**

Run: `uv run pytest tests/test_db/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add src/shuttle/db/
git commit -m "feat: add database engine with SQLite WAL mode and async session factory"
```

---

### Task 4: Repository Layer (CRUD)

**Files:**
- Create: `src/shuttle/db/repository.py`
- Create: `tests/test_db/test_repository.py`

- [ ] **Step 1: Write the test**

```python
"""Tests for repository CRUD operations."""

import pytest

from shuttle.db.models import Node, SecurityRule
from shuttle.db.repository import NodeRepo, RuleRepo


@pytest.mark.asyncio
async def test_node_repo_create_and_get(db_session):
    repo = NodeRepo(db_session)
    node = await repo.create(
        name="dev", host="1.2.3.4", port=22, username="root",
        auth_type="password", encrypted_credential="enc",
    )
    assert node.id is not None

    fetched = await repo.get_by_name("dev")
    assert fetched is not None
    assert fetched.host == "1.2.3.4"


@pytest.mark.asyncio
async def test_node_repo_list(db_session):
    repo = NodeRepo(db_session)
    await repo.create(name="a", host="1.1.1.1", port=22, username="u", auth_type="password", encrypted_credential="e")
    await repo.create(name="b", host="2.2.2.2", port=22, username="u", auth_type="password", encrypted_credential="e")
    nodes = await repo.list_all()
    assert len(nodes) == 2


@pytest.mark.asyncio
async def test_node_repo_update(db_session):
    repo = NodeRepo(db_session)
    node = await repo.create(name="x", host="h", port=22, username="u", auth_type="password", encrypted_credential="e")
    updated = await repo.update(node.id, host="new-host")
    assert updated.host == "new-host"


@pytest.mark.asyncio
async def test_node_repo_delete(db_session):
    repo = NodeRepo(db_session)
    node = await repo.create(name="del", host="h", port=22, username="u", auth_type="password", encrypted_credential="e")
    await repo.delete(node.id)
    assert await repo.get_by_name("del") is None


@pytest.mark.asyncio
async def test_rule_repo_create_and_list_ordered(db_session):
    repo = RuleRepo(db_session)
    await repo.create(pattern=r"sudo .*", level="confirm", description="sudo", priority=20)
    await repo.create(pattern=r"rm -rf /", level="block", description="rm root", priority=10)
    rules = await repo.list_all()
    assert len(rules) == 2
    assert rules[0].priority == 10  # Lower priority number = higher priority = first


@pytest.mark.asyncio
async def test_rule_repo_reorder(db_session):
    repo = RuleRepo(db_session)
    r1 = await repo.create(pattern="a", level="warn", description="", priority=1)
    r2 = await repo.create(pattern="b", level="warn", description="", priority=2)
    await repo.reorder([r2.id, r1.id])
    rules = await repo.list_all()
    assert rules[0].id == r2.id
    assert rules[0].priority == 0
    assert rules[1].id == r1.id
    assert rules[1].priority == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_db/test_repository.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write src/shuttle/db/repository.py**

```python
"""Data access layer — repository pattern for CRUD operations."""

from datetime import datetime, timezone

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Node, SecurityRule, Session, CommandLog, AppConfig


class NodeRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> Node:
        node = Node(**kwargs)
        self.session.add(node)
        await self.session.commit()
        await self.session.refresh(node)
        return node

    async def get_by_id(self, node_id: str) -> Node | None:
        result = await self.session.execute(select(Node).where(Node.id == node_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Node | None:
        result = await self.session.execute(select(Node).where(Node.name == name))
        return result.scalar_one_or_none()

    async def list_all(self, tag: str | None = None) -> list[Node]:
        stmt = select(Node).order_by(Node.name)
        result = await self.session.execute(stmt)
        nodes = list(result.scalars().all())
        if tag:
            nodes = [n for n in nodes if n.tags and tag in n.tags]
        return nodes

    async def update(self, node_id: str, **kwargs) -> Node:
        stmt = update(Node).where(Node.id == node_id).values(**kwargs)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(node_id)

    async def delete(self, node_id: str) -> None:
        stmt = delete(Node).where(Node.id == node_id)
        await self.session.execute(stmt)
        await self.session.commit()


class RuleRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> SecurityRule:
        rule = SecurityRule(**kwargs)
        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)
        return rule

    async def get_by_id(self, rule_id: str) -> SecurityRule | None:
        result = await self.session.execute(select(SecurityRule).where(SecurityRule.id == rule_id))
        return result.scalar_one_or_none()

    async def list_all(self, node_id: str | None = None) -> list[SecurityRule]:
        stmt = select(SecurityRule).order_by(SecurityRule.priority)
        if node_id is not None:
            stmt = stmt.where(
                (SecurityRule.node_id == node_id) | (SecurityRule.node_id.is_(None))
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, rule_id: str, **kwargs) -> SecurityRule:
        stmt = update(SecurityRule).where(SecurityRule.id == rule_id).values(**kwargs)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(rule_id)

    async def delete(self, rule_id: str) -> None:
        stmt = delete(SecurityRule).where(SecurityRule.id == rule_id)
        await self.session.execute(stmt)
        await self.session.commit()

    async def reorder(self, ids: list[str]) -> None:
        for priority, rule_id in enumerate(ids):
            stmt = update(SecurityRule).where(SecurityRule.id == rule_id).values(priority=priority)
            await self.session.execute(stmt)
        await self.session.commit()


class SessionRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> Session:
        s = Session(**kwargs)
        self.session.add(s)
        await self.session.commit()
        await self.session.refresh(s)
        return s

    async def get_by_id(self, session_id: str) -> Session | None:
        result = await self.session.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Session]:
        stmt = select(Session).where(Session.status == "active").order_by(Session.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def close(self, session_id: str) -> None:
        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(status="closed", closed_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_working_dir(self, session_id: str, working_directory: str) -> None:
        stmt = update(Session).where(Session.id == session_id).values(working_directory=working_directory)
        await self.session.execute(stmt)
        await self.session.commit()


class LogRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> CommandLog:
        log = CommandLog(**kwargs)
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def list_by_session(self, session_id: str, limit: int = 100, offset: int = 0) -> list[CommandLog]:
        stmt = (
            select(CommandLog)
            .where(CommandLog.session_id == session_id)
            .order_by(CommandLog.executed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ConfigRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> AppConfig | None:
        result = await self.session.execute(select(AppConfig).where(AppConfig.key == key))
        return result.scalar_one_or_none()

    async def set(self, key: str, value) -> AppConfig:
        existing = await self.get(key)
        if existing:
            existing.value = value
        else:
            existing = AppConfig(key=key, value=value)
            self.session.add(existing)
        await self.session.commit()
        await self.session.refresh(existing)
        return existing
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_db/test_repository.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/shuttle/db/repository.py tests/test_db/test_repository.py
git commit -m "feat: add repository layer with CRUD for Node, SecurityRule, Session, CommandLog"
```

---

### Task 5: Config & Credentials

**Files:**
- Create: `src/shuttle/core/config.py`
- Create: `src/shuttle/core/credentials.py`
- Create: `tests/test_core/test_config.py`
- Create: `tests/test_core/test_credentials.py`

- [ ] **Step 1: Write tests for credentials**

```python
"""Tests for credential encryption/decryption."""

import pytest

from shuttle.core.credentials import CredentialManager


def test_encrypt_decrypt_roundtrip(tmp_shuttle_dir):
    mgr = CredentialManager(tmp_shuttle_dir)
    plaintext = "my-secret-password"
    encrypted = mgr.encrypt(plaintext)
    assert encrypted != plaintext
    decrypted = mgr.decrypt(encrypted)
    assert decrypted == plaintext


def test_keyfile_created_on_first_use(tmp_shuttle_dir):
    mgr = CredentialManager(tmp_shuttle_dir)
    mgr.encrypt("test")
    keyfile = tmp_shuttle_dir / "keyfile"
    assert keyfile.exists()


def test_keyfile_reused_across_instances(tmp_shuttle_dir):
    mgr1 = CredentialManager(tmp_shuttle_dir)
    encrypted = mgr1.encrypt("secret")

    mgr2 = CredentialManager(tmp_shuttle_dir)
    assert mgr2.decrypt(encrypted) == "secret"


def test_decrypt_fails_with_wrong_key(tmp_shuttle_dir, tmp_path):
    mgr1 = CredentialManager(tmp_shuttle_dir)
    encrypted = mgr1.encrypt("data")

    other_dir = tmp_path / "other"
    other_dir.mkdir()
    mgr2 = CredentialManager(other_dir)

    with pytest.raises(Exception):
        mgr2.decrypt(encrypted)
```

- [ ] **Step 2: Write tests for config**

```python
"""Tests for ShuttleConfig."""

from shuttle.core.config import ShuttleConfig


def test_default_config(tmp_shuttle_dir):
    config = ShuttleConfig(shuttle_dir=tmp_shuttle_dir)
    assert config.db_url is None  # Will use default SQLite
    assert config.pool_max_total == 50
    assert config.pool_idle_timeout == 300


def test_config_custom_values(tmp_shuttle_dir):
    config = ShuttleConfig(
        shuttle_dir=tmp_shuttle_dir,
        pool_max_total=10,
        pool_idle_timeout=60,
    )
    assert config.pool_max_total == 10
    assert config.pool_idle_timeout == 60
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_core/test_credentials.py tests/test_core/test_config.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 4: Write src/shuttle/core/credentials.py**

```python
"""Credential encryption and keyfile management."""

import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet


class CredentialManager:
    """Manages encryption/decryption of SSH credentials using Fernet."""

    def __init__(self, shuttle_dir: Path):
        self._shuttle_dir = shuttle_dir
        self._keyfile = shuttle_dir / "keyfile"
        self._fernet: Fernet | None = None

    def _ensure_key(self) -> Fernet:
        if self._fernet is not None:
            return self._fernet

        if self._keyfile.exists():
            key = self._keyfile.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            self._shuttle_dir.mkdir(parents=True, exist_ok=True)
            self._keyfile.write_bytes(key)
            os.chmod(self._keyfile, stat.S_IRUSR | stat.S_IWUSR)  # 600

        self._fernet = Fernet(key)
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        fernet = self._ensure_key()
        return fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        fernet = self._ensure_key()
        return fernet.decrypt(encrypted.encode()).decode()
```

- [ ] **Step 5: Write src/shuttle/core/config.py**

```python
"""Shuttle global configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

DEFAULT_SHUTTLE_DIR = Path.home() / ".shuttle"


class ShuttleConfig(BaseSettings):
    """Global Shuttle configuration with defaults."""

    shuttle_dir: Path = Field(default=DEFAULT_SHUTTLE_DIR)
    db_url: str | None = Field(default=None, description="Database URL override")
    web_host: str = Field(default="127.0.0.1")
    web_port: int = Field(default=9876)

    # Connection pool defaults
    pool_max_total: int = Field(default=50)
    pool_max_per_node: int = Field(default=5)
    pool_idle_timeout: int = Field(default=300)
    pool_max_lifetime: int = Field(default=3600)
    pool_queue_size: int = Field(default=10)

    model_config = {"env_prefix": "SHUTTLE_"}
```

- [ ] **Step 6: Update src/shuttle/core/__init__.py**

```python
"""Shuttle core engine."""

from .config import ShuttleConfig
from .credentials import CredentialManager

__all__ = ["ShuttleConfig", "CredentialManager"]
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/test_core/ -v`
Expected: All 6 tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/shuttle/core/ tests/test_core/
git commit -m "feat: add ShuttleConfig and CredentialManager with Fernet encryption"
```

---

### Task 6: Command Security (CommandGuard)

**Files:**
- Create: `src/shuttle/core/security.py`
- Create: `tests/test_core/test_security.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for command security layer."""

import time

import pytest
import pytest_asyncio

from shuttle.core.security import (
    CommandGuard,
    ConfirmTokenStore,
    SecurityDecision,
    SecurityLevel,
)


class TestSecurityLevel:
    def test_enum_values(self):
        assert SecurityLevel.BLOCK == "block"
        assert SecurityLevel.CONFIRM == "confirm"
        assert SecurityLevel.WARN == "warn"
        assert SecurityLevel.ALLOW == "allow"


class TestCommandGuard:
    def setup_method(self):
        self.guard = CommandGuard()
        self.guard.load_rules([
            {"pattern": r"^rm -rf /$", "level": "block", "priority": 1, "node_id": None, "enabled": True},
            {"pattern": r"sudo .*", "level": "confirm", "priority": 10, "node_id": None, "enabled": True},
            {"pattern": r"pip install", "level": "warn", "priority": 20, "node_id": None, "enabled": True},
        ])

    def test_block_command(self):
        decision = self.guard.evaluate("rm -rf /", node_id=None, bypass_patterns=set())
        assert decision.level == SecurityLevel.BLOCK

    def test_confirm_command(self):
        decision = self.guard.evaluate("sudo apt update", node_id=None, bypass_patterns=set())
        assert decision.level == SecurityLevel.CONFIRM

    def test_warn_command(self):
        decision = self.guard.evaluate("pip install requests", node_id=None, bypass_patterns=set())
        assert decision.level == SecurityLevel.WARN

    def test_allow_command(self):
        decision = self.guard.evaluate("ls -la", node_id=None, bypass_patterns=set())
        assert decision.level == SecurityLevel.ALLOW

    def test_bypass_patterns_skip_confirm(self):
        decision = self.guard.evaluate(
            "sudo apt update", node_id=None, bypass_patterns={r"sudo .*"}
        )
        assert decision.level == SecurityLevel.ALLOW

    def test_bypass_cannot_skip_block(self):
        decision = self.guard.evaluate(
            "rm -rf /", node_id=None, bypass_patterns={r"^rm -rf /$"}
        )
        assert decision.level == SecurityLevel.BLOCK

    def test_disabled_rule_ignored(self):
        self.guard.load_rules([
            {"pattern": r"sudo .*", "level": "block", "priority": 1, "node_id": None, "enabled": False},
        ])
        decision = self.guard.evaluate("sudo ls", node_id=None, bypass_patterns=set())
        assert decision.level == SecurityLevel.ALLOW

    def test_invalid_regex_rejected(self):
        with pytest.raises(ValueError, match="Invalid regex"):
            self.guard.load_rules([
                {"pattern": r"[invalid", "level": "block", "priority": 1, "node_id": None, "enabled": True},
            ])


class TestConfirmTokenStore:
    def test_create_and_validate(self):
        store = ConfirmTokenStore()
        token = store.create("sudo ls", "node-1")
        assert store.validate(token, "sudo ls", "node-1") is True

    def test_token_is_one_time(self):
        store = ConfirmTokenStore()
        token = store.create("cmd", "n")
        assert store.validate(token, "cmd", "n") is True
        assert store.validate(token, "cmd", "n") is False  # Used up

    def test_token_wrong_command(self):
        store = ConfirmTokenStore()
        token = store.create("sudo ls", "node-1")
        assert store.validate(token, "sudo rm", "node-1") is False

    def test_token_wrong_node(self):
        store = ConfirmTokenStore()
        token = store.create("cmd", "node-1")
        assert store.validate(token, "cmd", "node-2") is False

    def test_token_expired(self):
        store = ConfirmTokenStore(ttl_seconds=0)  # Immediate expiry
        token = store.create("cmd", "n")
        time.sleep(0.01)
        assert store.validate(token, "cmd", "n") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_core/test_security.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write src/shuttle/core/security.py**

```python
"""Command security layer — 4-level classification with regex matching."""

import re
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum


class SecurityLevel(str, Enum):
    BLOCK = "block"
    CONFIRM = "confirm"
    WARN = "warn"
    ALLOW = "allow"


@dataclass
class SecurityDecision:
    level: SecurityLevel
    matched_rule: dict | None = None
    message: str = ""


@dataclass
class _CompiledRule:
    pattern: re.Pattern
    pattern_str: str
    level: SecurityLevel
    priority: int
    node_id: str | None
    enabled: bool


@dataclass
class _ConfirmToken:
    command: str
    node_id: str
    created_at: float


class ConfirmTokenStore:
    """In-memory store for one-time confirmation tokens."""

    def __init__(self, ttl_seconds: int = 60):
        self._tokens: dict[str, _ConfirmToken] = {}
        self._ttl = ttl_seconds

    def create(self, command: str, node_id: str) -> str:
        self._cleanup_if_needed()
        token = secrets.token_urlsafe(32)
        self._tokens[token] = _ConfirmToken(
            command=command, node_id=node_id, created_at=time.monotonic()
        )
        return token

    def validate(self, token: str, command: str, node_id: str) -> bool:
        ct = self._tokens.pop(token, None)  # One-time: delete on lookup
        if ct is None:
            return False
        if time.monotonic() - ct.created_at > self._ttl:
            return False
        if ct.command != command or ct.node_id != node_id:
            return False
        return True

    def _cleanup_if_needed(self) -> None:
        if len(self._tokens) > 100:
            now = time.monotonic()
            self._tokens = {
                k: v for k, v in self._tokens.items()
                if now - v.created_at <= self._ttl
            }


class CommandGuard:
    """Evaluates commands against security rules."""

    def __init__(self):
        self._rules: list[_CompiledRule] = []

    def load_rules(self, rules: list[dict]) -> None:
        compiled = []
        for r in rules:
            try:
                pattern = re.compile(r["pattern"])
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{r['pattern']}': {e}")
            compiled.append(_CompiledRule(
                pattern=pattern,
                pattern_str=r["pattern"],
                level=SecurityLevel(r["level"]),
                priority=r["priority"],
                node_id=r.get("node_id"),
                enabled=r.get("enabled", True),
            ))
        self._rules = sorted(compiled, key=lambda r: r.priority)

    def evaluate(
        self,
        command: str,
        node_id: str | None,
        bypass_patterns: set[str],
    ) -> SecurityDecision:
        # Check rules in priority order
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.node_id is not None and rule.node_id != node_id:
                continue

            try:
                match = rule.pattern.search(command)
            except Exception:
                continue

            if match:
                # Block-level cannot be bypassed
                if rule.level == SecurityLevel.BLOCK:
                    return SecurityDecision(
                        level=SecurityLevel.BLOCK,
                        matched_rule={"pattern": rule.pattern_str, "level": rule.level.value},
                        message=f"Command blocked by rule: {rule.pattern_str}",
                    )

                # Check bypass patterns (session-level bypass)
                if rule.pattern_str in bypass_patterns:
                    return SecurityDecision(level=SecurityLevel.ALLOW)

                return SecurityDecision(
                    level=rule.level,
                    matched_rule={"pattern": rule.pattern_str, "level": rule.level.value},
                )

        return SecurityDecision(level=SecurityLevel.ALLOW)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_core/test_security.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/shuttle/core/security.py tests/test_core/test_security.py
git commit -m "feat: add CommandGuard with 4-level security and ConfirmTokenStore"
```

---

### Task 7: Connection Pool

**Files:**
- Create: `src/shuttle/core/connection_pool.py`
- Create: `src/shuttle/core/proxy.py`
- Create: `tests/test_core/test_connection_pool.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for SSH connection pool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shuttle.core.connection_pool import ConnectionPool, PoolConfig, PooledConnection


@pytest.fixture
def pool_config():
    return PoolConfig(
        max_total=5, max_per_node=2, idle_timeout=10,
        max_lifetime=60, queue_size=3,
    )


class TestPoolConfig:
    def test_defaults(self):
        config = PoolConfig()
        assert config.max_total == 50
        assert config.max_per_node == 5


class TestPooledConnection:
    def test_is_expired_by_idle(self):
        conn = PooledConnection(
            connection=MagicMock(), node_id="n", created_at=0, last_used_at=0,
        )
        assert conn.is_expired(idle_timeout=10, max_lifetime=3600, now=15) is True

    def test_is_expired_by_lifetime(self):
        conn = PooledConnection(
            connection=MagicMock(), node_id="n", created_at=0, last_used_at=50,
        )
        assert conn.is_expired(idle_timeout=300, max_lifetime=60, now=61) is True

    def test_not_expired(self):
        conn = PooledConnection(
            connection=MagicMock(), node_id="n", created_at=0, last_used_at=5,
        )
        assert conn.is_expired(idle_timeout=300, max_lifetime=3600, now=10) is False


class TestConnectionPool:
    @pytest.mark.asyncio
    async def test_acquire_creates_connection(self, pool_config):
        pool = ConnectionPool(pool_config)
        mock_conn = AsyncMock()

        with patch.object(pool, "_create_connection", return_value=mock_conn):
            async with pool.connection("node-1") as conn:
                assert conn.node_id == "node-1"
                assert conn.connection == mock_conn

    @pytest.mark.asyncio
    async def test_release_returns_to_pool(self, pool_config):
        pool_config.idle_timeout = 9999  # Ensure connection won't expire
        pool_config.max_lifetime = 9999
        pool = ConnectionPool(pool_config)
        mock_conn = AsyncMock()
        call_count = 0

        async def _create_once(node_id):
            nonlocal call_count
            call_count += 1
            return mock_conn

        with patch.object(pool, "_create_connection", side_effect=_create_once):
            async with pool.connection("node-1") as conn:
                pass  # Released on exit

            # Second acquire should reuse the idle connection
            async with pool.connection("node-1") as conn2:
                assert conn2.connection == mock_conn

        assert call_count == 1  # Only created once, reused on second acquire

    @pytest.mark.asyncio
    async def test_max_per_node_enforced(self, pool_config):
        pool_config.max_per_node = 1
        pool = ConnectionPool(pool_config)
        mock_conn = AsyncMock()

        with patch.object(pool, "_create_connection", return_value=mock_conn):
            conn1 = await pool.acquire("node-1")
            # Pool is full for this node, second acquire should wait/fail
            # (Since we haven't released conn1, the pool should be at capacity)
            assert pool._active_count("node-1") == 1

            await pool.release(conn1)
            assert pool._active_count("node-1") == 0

    @pytest.mark.asyncio
    async def test_close_all(self, pool_config):
        pool = ConnectionPool(pool_config)
        mock_conn = AsyncMock()

        with patch.object(pool, "_create_connection", return_value=mock_conn):
            async with pool.connection("node-1") as conn:
                pass

        await pool.close_all()
        assert pool._active_total() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_core/test_connection_pool.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write src/shuttle/core/proxy.py**

```python
"""SSH Jump Host (bastion) proxy support."""

from dataclasses import dataclass

import asyncssh


@dataclass
class NodeConnectInfo:
    host: str
    port: int
    username: str
    password: str | None = None
    private_key_path: str | None = None
    passphrase: str | None = None
    jump_host: "NodeConnectInfo | None" = None


async def connect_ssh(info: NodeConnectInfo) -> asyncssh.SSHClientConnection:
    """Connect to SSH node, optionally through a jump host."""
    kwargs: dict = {
        "host": info.host,
        "port": info.port,
        "username": info.username,
        "known_hosts": None,
    }

    if info.private_key_path:
        kwargs["client_keys"] = [info.private_key_path]
        if info.passphrase:
            kwargs["passphrase"] = info.passphrase
    elif info.password:
        kwargs["password"] = info.password

    if info.jump_host:
        tunnel = await connect_ssh(info.jump_host)
        kwargs["tunnel"] = tunnel

    return await asyncssh.connect(**kwargs)
```

- [ ] **Step 4: Write src/shuttle/core/connection_pool.py**

```python
"""SSH connection pool with context manager, health checks, and eviction."""

import asyncio
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import asyncssh

from .proxy import NodeConnectInfo, connect_ssh


@dataclass
class PoolConfig:
    max_total: int = 50
    max_per_node: int = 5
    idle_timeout: int = 300
    max_lifetime: int = 3600
    queue_size: int = 10


@dataclass
class PooledConnection:
    connection: asyncssh.SSHClientConnection
    node_id: str
    created_at: float
    last_used_at: float

    def is_expired(self, idle_timeout: int, max_lifetime: int, now: float | None = None) -> bool:
        now = now or time.monotonic()
        if now - self.last_used_at > idle_timeout:
            return True
        if now - self.created_at > max_lifetime:
            return True
        return False

    def touch(self) -> None:
        self.last_used_at = time.monotonic()


class ConnectionPool:
    """Async SSH connection pool with lazy creation and automatic eviction."""

    def __init__(self, config: PoolConfig | None = None):
        self._config = config or PoolConfig()
        self._idle: dict[str, list[PooledConnection]] = {}  # node_id -> idle connections
        self._active: dict[str, int] = {}  # node_id -> count of active connections
        self._lock = asyncio.Lock()
        self._node_connect_infos: dict[str, NodeConnectInfo] = {}
        self._eviction_task: asyncio.Task | None = None

    def register_node(self, node_id: str, info: NodeConnectInfo) -> None:
        self._node_connect_infos[node_id] = info

    def unregister_node(self, node_id: str) -> None:
        self._node_connect_infos.pop(node_id, None)

    @asynccontextmanager
    async def connection(self, node_id: str) -> AsyncIterator[PooledConnection]:
        conn = await self.acquire(node_id)
        try:
            yield conn
        finally:
            await self.release(conn)

    async def acquire(self, node_id: str) -> PooledConnection:
        async with self._lock:
            # Try to get an idle connection
            idle_list = self._idle.get(node_id, [])
            while idle_list:
                conn = idle_list.pop()
                if not conn.is_expired(self._config.idle_timeout, self._config.max_lifetime):
                    conn.touch()
                    self._active[node_id] = self._active.get(node_id, 0) + 1
                    return conn
                else:
                    # Expired, close it
                    try:
                        conn.connection.close()
                    except Exception:
                        pass

            # No idle connection, create new one if under limit
            active = self._active.get(node_id, 0)
            total = self._active_total() + sum(len(v) for v in self._idle.values())
            if active >= self._config.max_per_node:
                raise RuntimeError(f"Connection pool exhausted for node '{node_id}' (max_per_node={self._config.max_per_node})")
            if total >= self._config.max_total:
                raise RuntimeError(f"Global connection pool exhausted (max_total={self._config.max_total})")

            # Reserve slot atomically before releasing lock
            self._active[node_id] = active + 1

        # Create outside lock to avoid blocking
        try:
            ssh_conn = await self._create_connection(node_id)
        except Exception:
            # Unreserve slot on failure
            async with self._lock:
                self._active[node_id] = self._active.get(node_id, 1) - 1
            raise

        now = time.monotonic()
        pooled = PooledConnection(
            connection=ssh_conn, node_id=node_id, created_at=now, last_used_at=now,
        )
        return pooled

    async def release(self, conn: PooledConnection) -> None:
        async with self._lock:
            active = self._active.get(conn.node_id, 0)
            if active > 0:
                self._active[conn.node_id] = active - 1
            conn.touch()
            if conn.node_id not in self._idle:
                self._idle[conn.node_id] = []
            self._idle[conn.node_id].append(conn)

    async def _create_connection(self, node_id: str) -> asyncssh.SSHClientConnection:
        info = self._node_connect_infos.get(node_id)
        if info is None:
            raise ValueError(f"No connection info registered for node '{node_id}'")
        return await connect_ssh(info)

    async def evict_expired(self) -> int:
        evicted = 0
        async with self._lock:
            for node_id, idle_list in list(self._idle.items()):
                remaining = []
                for conn in idle_list:
                    if conn.is_expired(self._config.idle_timeout, self._config.max_lifetime):
                        try:
                            conn.connection.close()
                        except Exception:
                            pass
                        evicted += 1
                    else:
                        remaining.append(conn)
                self._idle[node_id] = remaining
        return evicted

    async def close_all(self) -> None:
        async with self._lock:
            for idle_list in self._idle.values():
                for conn in idle_list:
                    try:
                        conn.connection.close()
                    except Exception:
                        pass
            self._idle.clear()
            self._active.clear()
        if self._eviction_task and not self._eviction_task.done():
            self._eviction_task.cancel()

    async def close_node(self, node_id: str) -> None:
        async with self._lock:
            for conn in self._idle.pop(node_id, []):
                try:
                    conn.connection.close()
                except Exception:
                    pass
            self._active.pop(node_id, None)

    def _active_count(self, node_id: str) -> int:
        return self._active.get(node_id, 0)

    def _active_total(self) -> int:
        return sum(self._active.values())

    async def start_eviction_loop(self, interval: int = 60) -> None:
        async def _loop():
            while True:
                await asyncio.sleep(interval)
                await self.evict_expired()
        self._eviction_task = asyncio.create_task(_loop())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_core/test_connection_pool.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/shuttle/core/connection_pool.py src/shuttle/core/proxy.py tests/test_core/test_connection_pool.py
git commit -m "feat: add SSH connection pool with context manager, eviction, and jump host support"
```

---

### Task 8: Session Manager

**Files:**
- Create: `src/shuttle/core/session.py`
- Create: `tests/test_core/test_session.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for session management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shuttle.core.session import CommandResult, SessionManager, SSHSession


class TestSSHSession:
    def test_create_session(self):
        session = SSHSession(node_id="node-1", working_directory="/home/user")
        assert session.session_id is not None
        assert session.status == "active"
        assert session.bypass_patterns == set()

    def test_add_bypass_pattern(self):
        session = SSHSession(node_id="n", working_directory="/")
        session.bypass_patterns.add(r"sudo .*")
        assert r"sudo .*" in session.bypass_patterns


class TestSessionManager:
    @pytest.mark.asyncio
    async def test_create_session(self):
        mock_pool = MagicMock()
        mock_db_session_factory = AsyncMock()
        mgr = SessionManager(pool=mock_pool, db_session_factory=mock_db_session_factory)

        # Mock the SSH connection to return a pwd result
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.stdout = "/home/testuser\n"
        mock_result.exit_status = 0
        mock_conn.connection.run = AsyncMock(return_value=mock_result)

        with patch.object(mgr, "_run_on_node", return_value="/home/testuser"):
            session = await mgr.create("node-1")

        assert session.node_id == "node-1"
        assert session.working_directory == "/home/testuser"
        assert session.status == "active"

    def test_wrap_command_with_cd(self):
        cmd = SessionManager._wrap_command("ls -la", "/home/user")
        assert "cd '/home/user'" in cmd or "cd /home/user" in cmd
        assert "ls -la" in cmd
        assert "---SHUTTLE_PWD---" in cmd
        assert cmd.endswith("pwd")

    def test_wrap_command_quotes_special_chars(self):
        cmd = SessionManager._wrap_command("ls", "/home/user name")
        assert "'/home/user name'" in cmd
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_core/test_session.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write src/shuttle/core/session.py**

```python
"""SSH session management with working directory tracking."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    working_directory: str  # Updated pwd after command


@dataclass
class SSHSession:
    node_id: str
    working_directory: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "active"  # active / idle / closed
    bypass_patterns: set[str] = field(default_factory=set)
    env_vars: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


PWD_SENTINEL = "---SHUTTLE_PWD---"
OUTPUT_MAX_BYTES = 10 * 1024 * 1024  # 10MB


class SessionManager:
    """Manages SSH sessions with working directory tracking."""

    def __init__(self, pool, db_session_factory=None):
        self._pool = pool
        self._db_session_factory = db_session_factory
        self._sessions: dict[str, SSHSession] = {}

    async def create(self, node_id: str) -> SSHSession:
        # Get initial working directory
        initial_pwd = await self._run_on_node(node_id, "pwd")
        session = SSHSession(
            node_id=node_id,
            working_directory=initial_pwd.strip(),
        )
        self._sessions[session.session_id] = session

        # Persist to DB for Web panel visibility
        if self._db_session_factory:
            from shuttle.db.repository import SessionRepo
            async with self._db_session_factory() as db_session:
                repo = SessionRepo(db_session)
                await repo.create(
                    id=session.session_id,
                    node_id=node_id,
                    working_directory=session.working_directory,
                    status="active",
                )

        return session

    def get(self, session_id: str) -> SSHSession | None:
        return self._sessions.get(session_id)

    async def execute(self, session_id: str, command: str, timeout: int = 30) -> CommandResult:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found")

        import time
        start = time.monotonic()

        wrapped = self._wrap_command(command, session.working_directory)

        async with self._pool.connection(session.node_id) as conn:
            import asyncio
            result = await asyncio.wait_for(conn.connection.run(wrapped), timeout=timeout)

        duration_ms = int((time.monotonic() - start) * 1000)

        # Parse output: split at sentinel to get stdout and pwd
        raw_stdout = result.stdout or ""

        # Truncate if too large
        if len(raw_stdout) > OUTPUT_MAX_BYTES:
            raw_stdout = raw_stdout[:OUTPUT_MAX_BYTES] + "\n[OUTPUT TRUNCATED AT 10MB]"

        if PWD_SENTINEL in raw_stdout:
            parts = raw_stdout.rsplit(PWD_SENTINEL, 1)
            actual_stdout = parts[0].rstrip("\n")
            new_pwd = parts[1].strip()
            if new_pwd:
                session.working_directory = new_pwd
        else:
            actual_stdout = raw_stdout

        session.last_active_at = datetime.now(timezone.utc)

        cmd_result = CommandResult(
            stdout=actual_stdout,
            stderr=result.stderr or "",
            exit_code=result.exit_status or 0,
            duration_ms=duration_ms,
            working_directory=session.working_directory,
        )

        # Persist working directory update and command log to DB
        if self._db_session_factory:
            from shuttle.db.repository import SessionRepo, LogRepo
            async with self._db_session_factory() as db_session:
                await SessionRepo(db_session).update_working_dir(
                    session.session_id, session.working_directory
                )
                # Truncate stdout for DB storage (first+last 5000 chars if > 64KB)
                db_stdout = actual_stdout
                if len(db_stdout) > 64 * 1024:
                    db_stdout = db_stdout[:5000] + "\n...[TRUNCATED]...\n" + db_stdout[-5000:]
                await LogRepo(db_session).create(
                    session_id=session.session_id,
                    node_id=session.node_id,
                    command=command,
                    exit_code=cmd_result.exit_code,
                    stdout=db_stdout,
                    stderr=cmd_result.stderr,
                    duration_ms=duration_ms,
                )

        return cmd_result

    async def close(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session:
            session.status = "closed"

    def list_active(self) -> list[SSHSession]:
        return [s for s in self._sessions.values() if s.status == "active"]

    async def _run_on_node(self, node_id: str, command: str) -> str:
        async with self._pool.connection(node_id) as conn:
            result = await conn.connection.run(command)
            return result.stdout or ""

    @staticmethod
    def _wrap_command(command: str, working_directory: str) -> str:
        import shlex
        return f"cd {shlex.quote(working_directory)} && {command}; echo '{PWD_SENTINEL}'; pwd"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_core/test_session.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/shuttle/core/session.py tests/test_core/test_session.py
git commit -m "feat: add SessionManager with working directory tracking via pwd sentinel"
```

---

### Task 9: MCP Tools

**Files:**
- Create: `src/shuttle/mcp/tools.py`
- Create: `tests/test_mcp/test_tools.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for MCP tool definitions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shuttle.core.security import SecurityDecision, SecurityLevel
from shuttle.core.session import CommandResult
from shuttle.mcp.tools import register_tools


@pytest.fixture
def mock_deps():
    """Create mock dependencies for tools."""
    pool = MagicMock()
    guard = MagicMock()
    token_store = MagicMock()
    session_mgr = MagicMock()
    db_session_factory = AsyncMock()
    node_repo = AsyncMock()
    return {
        "pool": pool,
        "guard": guard,
        "token_store": token_store,
        "session_mgr": session_mgr,
        "db_session_factory": db_session_factory,
        "node_repo_factory": lambda s: node_repo,
        "node_repo": node_repo,
    }


class TestSshExecuteLogic:
    """Test the core logic of ssh_execute (not the MCP decorator)."""

    @pytest.mark.asyncio
    async def test_allowed_command_executes(self, mock_deps):
        mock_deps["guard"].evaluate.return_value = SecurityDecision(level=SecurityLevel.ALLOW)
        mock_deps["session_mgr"].execute = AsyncMock(
            return_value=CommandResult(
                stdout="file.txt", stderr="", exit_code=0,
                duration_ms=10, working_directory="/home",
            )
        )
        mock_deps["session_mgr"].get.return_value = MagicMock(
            node_id="n1", bypass_patterns=set()
        )

        from shuttle.mcp.tools import _execute_command_logic
        result = await _execute_command_logic(
            command="ls",
            node=None,
            session_id="s1",
            timeout=30,
            confirm_token=None,
            bypass_scope=None,
            **mock_deps,
        )
        assert "file.txt" in result

    @pytest.mark.asyncio
    async def test_blocked_command_rejected(self, mock_deps):
        mock_deps["guard"].evaluate.return_value = SecurityDecision(
            level=SecurityLevel.BLOCK,
            message="Command blocked",
        )
        mock_deps["session_mgr"].get.return_value = MagicMock(
            node_id="n1", bypass_patterns=set()
        )

        from shuttle.mcp.tools import _execute_command_logic
        result = await _execute_command_logic(
            command="rm -rf /",
            node=None,
            session_id="s1",
            timeout=30,
            confirm_token=None,
            bypass_scope=None,
            **mock_deps,
        )
        assert "BLOCKED" in result

    @pytest.mark.asyncio
    async def test_confirm_returns_token_request(self, mock_deps):
        mock_deps["guard"].evaluate.return_value = SecurityDecision(
            level=SecurityLevel.CONFIRM,
            matched_rule={"pattern": "sudo .*", "level": "confirm"},
        )
        mock_deps["session_mgr"].get.return_value = MagicMock(
            node_id="n1", bypass_patterns=set()
        )
        mock_deps["token_store"].create.return_value = "test-token-123"

        from shuttle.mcp.tools import _execute_command_logic
        result = await _execute_command_logic(
            command="sudo ls",
            node=None,
            session_id="s1",
            timeout=30,
            confirm_token=None,
            bypass_scope=None,
            **mock_deps,
        )
        assert "CONFIRMATION REQUIRED" in result
        assert "test-token-123" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mcp/test_tools.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write src/shuttle/mcp/tools.py**

```python
"""MCP tool definitions for Shuttle."""

from fastmcp import Context, FastMCP

from shuttle.core.security import CommandGuard, ConfirmTokenStore, SecurityLevel
from shuttle.core.session import SessionManager


def register_tools(
    mcp: FastMCP,
    pool,
    guard: CommandGuard,
    token_store: ConfirmTokenStore,
    session_mgr: SessionManager,
    db_session_factory,
    node_repo_factory,
) -> None:
    """Register all MCP tools on the given FastMCP instance."""

    @mcp.tool(name="ssh_execute")
    async def ssh_execute(
        command: str,
        node: str | None = None,
        session_id: str | None = None,
        timeout: int = 30,
        confirm_token: str | None = None,
        bypass_scope: str | None = None,
    ) -> str:
        """Execute command on remote SSH node."""
        return await _execute_command_logic(
            command=command,
            node=node,
            session_id=session_id,
            timeout=timeout,
            confirm_token=confirm_token,
            bypass_scope=bypass_scope,
            pool=pool,
            guard=guard,
            token_store=token_store,
            session_mgr=session_mgr,
            db_session_factory=db_session_factory,
            node_repo_factory=node_repo_factory,
        )

    @mcp.tool(name="ssh_list_nodes")
    async def ssh_list_nodes() -> str:
        """List all configured SSH nodes and their status."""
        async with db_session_factory() as db_session:
            repo = node_repo_factory(db_session)
            nodes = await repo.list_all()
            if not nodes:
                return (
                    "No SSH nodes configured.\n\n"
                    "Add a node via CLI:\n"
                    "  shuttle node add --name dev --host 1.2.3.4 --user root --password xxx\n\n"
                    "Or start the web panel:\n"
                    "  shuttle web"
                )
            lines = ["SSH Nodes:"]
            for n in nodes:
                status_icon = {"online": "+", "offline": "x", "unknown": "?"}.get(n.status, "?")
                lines.append(f"  [{status_icon}] {n.name} — {n.username}@{n.host}:{n.port}")
            return "\n".join(lines)

    @mcp.tool(name="ssh_session_start")
    async def ssh_session_start(node: str) -> str:
        """Create a new SSH session on the specified node."""
        async with db_session_factory() as db_session:
            repo = node_repo_factory(db_session)
            node_obj = await repo.get_by_name(node)
            if not node_obj:
                return f"Node '{node}' not found."
        session = await session_mgr.create(node_obj.id)
        return (
            f"Session created.\n"
            f"  session_id: {session.session_id}\n"
            f"  node: {node}\n"
            f"  working_directory: {session.working_directory}"
        )

    @mcp.tool(name="ssh_session_end")
    async def ssh_session_end(session_id: str) -> str:
        """Close an SSH session."""
        session = session_mgr.get(session_id)
        if not session:
            return f"Session '{session_id}' not found."
        await session_mgr.close(session_id)
        return f"Session '{session_id}' closed."

    @mcp.tool(name="ssh_session_list")
    async def ssh_session_list() -> str:
        """List active SSH sessions."""
        sessions = session_mgr.list_active()
        if not sessions:
            return "No active sessions."
        lines = ["Active Sessions:"]
        for s in sessions:
            lines.append(f"  {s.session_id} — node={s.node_id} cwd={s.working_directory}")
        return "\n".join(lines)

    @mcp.tool(name="ssh_upload")
    async def ssh_upload(local_path: str, remote_path: str, node: str) -> str:
        """Upload file to remote node via SFTP."""
        async with db_session_factory() as db_session:
            repo = node_repo_factory(db_session)
            node_obj = await repo.get_by_name(node)
            if not node_obj:
                return f"Node '{node}' not found."
        async with pool.connection(node_obj.id) as conn:
            async with conn.connection.start_sftp_client() as sftp:
                await sftp.put(local_path, remote_path)
        return f"Uploaded {local_path} → {node}:{remote_path}"

    @mcp.tool(name="ssh_download")
    async def ssh_download(remote_path: str, local_path: str, node: str) -> str:
        """Download file from remote node via SFTP."""
        async with db_session_factory() as db_session:
            repo = node_repo_factory(db_session)
            node_obj = await repo.get_by_name(node)
            if not node_obj:
                return f"Node '{node}' not found."
        async with pool.connection(node_obj.id) as conn:
            async with conn.connection.start_sftp_client() as sftp:
                await sftp.get(remote_path, local_path)
        return f"Downloaded {node}:{remote_path} → {local_path}"


async def _execute_command_logic(
    command: str,
    node: str | None,
    session_id: str | None,
    timeout: int,
    confirm_token: str | None,
    bypass_scope: str | None,
    pool,
    guard: CommandGuard,
    token_store: ConfirmTokenStore,
    session_mgr: SessionManager,
    db_session_factory,
    node_repo_factory,
    **_kwargs,
) -> str:
    """Core logic for ssh_execute, extracted for testability."""

    # 1. Resolve node
    resolved_node_id = None
    bypass_patterns: set[str] = set()

    if session_id:
        session = session_mgr.get(session_id)
        if session:
            resolved_node_id = session.node_id
            bypass_patterns = session.bypass_patterns
    if resolved_node_id is None and node:
        async with db_session_factory() as db_session:
            repo = node_repo_factory(db_session)
            node_obj = await repo.get_by_name(node)
            if node_obj:
                resolved_node_id = node_obj.id
    if resolved_node_id is None:
        async with db_session_factory() as db_session:
            repo = node_repo_factory(db_session)
            all_nodes = await repo.list_all()
            if len(all_nodes) == 1:
                resolved_node_id = all_nodes[0].id
            else:
                names = [n.name for n in all_nodes]
                return f"Please specify a node. Available: {', '.join(names) if names else 'none configured'}"

    # 2. Security check
    decision = guard.evaluate(command, resolved_node_id, bypass_patterns)

    if decision.level == SecurityLevel.BLOCK:
        return f"BLOCKED: {decision.message}"

    if decision.level == SecurityLevel.CONFIRM:
        if confirm_token:
            if token_store.validate(confirm_token, command, resolved_node_id):
                # Token valid — add to session bypass if requested
                if bypass_scope == "session" and session_id and decision.matched_rule:
                    session = session_mgr.get(session_id)
                    if session:
                        session.bypass_patterns.add(decision.matched_rule["pattern"])
            else:
                return "Invalid or expired confirmation token. Please request a new one."
        else:
            token = token_store.create(command, resolved_node_id)
            rule_desc = decision.matched_rule["pattern"] if decision.matched_rule else "unknown"
            return (
                f"CONFIRMATION REQUIRED\n"
                f"Command: {command}\n"
                f"Matched rule: {rule_desc}\n\n"
                f"To execute, call again with:\n"
                f"  ssh_execute(command='{command}', confirm_token='{token}')"
            )

    # 2b. Warn-level: log warning but proceed
    if decision.level == SecurityLevel.WARN:
        from loguru import logger
        logger.warning(f"Warn-level command on node {resolved_node_id}: {command}")

    # 3. Execute
    if session_id and session_mgr.get(session_id):
        result = await session_mgr.execute(session_id, command, timeout)
        return result.stdout.strip() if result.stdout else ""
    else:
        # Stateless execution (no session)
        import time as _time
        start = _time.monotonic()
        async with pool.connection(resolved_node_id) as conn:
            import asyncio as _asyncio
            ssh_result = await _asyncio.wait_for(conn.connection.run(command), timeout=timeout)
        duration_ms = int((_time.monotonic() - start) * 1000)
        result_stdout = ssh_result.stdout or ""
        if len(result_stdout) > 10 * 1024 * 1024:
            result_stdout = result_stdout[:10 * 1024 * 1024] + "\n[OUTPUT TRUNCATED AT 10MB]"

        # Log to DB (inline, not fire-and-forget)
        try:
            async with db_session_factory() as db_s:
                from shuttle.db.repository import LogRepo
                db_stdout = result_stdout
                if len(db_stdout) > 64 * 1024:
                    db_stdout = db_stdout[:5000] + "\n...[TRUNCATED]...\n" + db_stdout[-5000:]
                await LogRepo(db_s).create(
                    session_id=None,  # No session for stateless execution
                    node_id=resolved_node_id,
                    command=command,
                    exit_code=ssh_result.exit_status or 0,
                    stdout=db_stdout,
                    stderr=ssh_result.stderr or "",
                    security_level=decision.level.value,
                    security_rule_id=decision.matched_rule.get("id") if decision.matched_rule else None,
                    bypassed=confirm_token is not None,
                    duration_ms=duration_ms,
                )
        except Exception:
            pass  # Log failure should not break command execution

        return result_stdout.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_mcp/test_tools.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/shuttle/mcp/tools.py tests/test_mcp/test_tools.py
git commit -m "feat: add MCP tools (ssh_execute, ssh_upload, ssh_download, ssh_session_*, ssh_list_nodes)"
```

---

### Task 10: MCP Server Orchestration

**Files:**
- Create: `src/shuttle/mcp/server.py`
- Create: `tests/test_mcp/test_server.py`
- Modify: `src/shuttle/mcp/__init__.py`

- [ ] **Step 1: Write test**

```python
"""Tests for MCP server creation."""

from unittest.mock import AsyncMock, patch

import pytest

from shuttle.mcp.server import create_mcp_server


@pytest.mark.asyncio
async def test_create_mcp_server_returns_fastmcp(tmp_shuttle_dir):
    """Verify create_mcp_server returns a configured FastMCP instance."""
    db_url = f"sqlite+aiosqlite:///{tmp_shuttle_dir / 'test.db'}"

    with patch("shuttle.mcp.server.ConnectionPool") as MockPool, \
         patch("shuttle.mcp.server.SessionManager") as MockSessionMgr:
        MockPool.return_value = AsyncMock()
        MockSessionMgr.return_value = AsyncMock()

        mcp = await create_mcp_server(
            shuttle_dir=tmp_shuttle_dir,
            db_url=db_url,
        )

    assert mcp is not None
    assert mcp.name == "shuttle"
    # Verify tools are registered
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "ssh_execute" in tool_names
    assert "ssh_list_nodes" in tool_names
    assert "ssh_session_start" in tool_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mcp/test_server.py -v`
Expected: FAIL (ImportError)

- [ ] **Step 3: Write src/shuttle/mcp/server.py**

```python
"""MCP server creation and startup orchestration."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import FastMCP

from shuttle.core.config import ShuttleConfig
from shuttle.core.connection_pool import ConnectionPool, PoolConfig
from shuttle.core.credentials import CredentialManager
from shuttle.core.proxy import NodeConnectInfo
from shuttle.core.security import CommandGuard, ConfirmTokenStore
from shuttle.core.session import SessionManager
from shuttle.db.engine import create_db_engine, create_session_factory, init_db
from shuttle.db.models import Node, SecurityRule
from shuttle.db.repository import NodeRepo, RuleRepo

from .tools import register_tools


async def create_mcp_server(
    shuttle_dir: Path | None = None,
    db_url: str | None = None,
) -> FastMCP:
    """Create and configure the Shuttle MCP server."""
    config = ShuttleConfig(shuttle_dir=shuttle_dir) if shuttle_dir else ShuttleConfig()
    config.shuttle_dir.mkdir(parents=True, exist_ok=True)

    # Write PID file
    pid_file = config.shuttle_dir / "mcp.pid"
    pid_file.write_text(str(os.getpid()))

    # Init DB
    engine = create_db_engine(db_url or config.db_url)
    await init_db(engine)
    session_factory = create_session_factory(engine)

    # Load security rules
    guard = CommandGuard()
    async with session_factory() as db_session:
        rule_repo = RuleRepo(db_session)
        rules = await rule_repo.list_all()
        guard.load_rules([
            {
                "pattern": r.pattern,
                "level": r.level,
                "priority": r.priority,
                "node_id": r.node_id,
                "enabled": r.enabled,
            }
            for r in rules
        ])

    # Init connection pool (lazy — no connections yet)
    pool_config = PoolConfig(
        max_total=config.pool_max_total,
        max_per_node=config.pool_max_per_node,
        idle_timeout=config.pool_idle_timeout,
        max_lifetime=config.pool_max_lifetime,
        queue_size=config.pool_queue_size,
    )
    pool = ConnectionPool(pool_config)

    # Register node connection infos for the pool
    cred_mgr = CredentialManager(config.shuttle_dir)
    async with session_factory() as db_session:
        node_repo = NodeRepo(db_session)
        nodes = await node_repo.list_all()
        for node in nodes:
            try:
                credential = cred_mgr.decrypt(node.encrypted_credential)
            except Exception:
                from loguru import logger
                logger.warning(
                    f"Could not decrypt credentials for node '{node.name}' — "
                    f"keyfile may be missing or corrupted. Re-add the node with 'shuttle node add'."
                )
                continue
            info = NodeConnectInfo(
                host=node.host,
                port=node.port,
                username=node.username,
                password=credential if node.auth_type == "password" else None,
                private_key_path=credential if node.auth_type == "key" else None,
            )
            pool.register_node(node.id, info)

    # Start background eviction loop
    await pool.start_eviction_loop(interval=60)

    # Token store and session manager
    token_store = ConfirmTokenStore()
    session_mgr = SessionManager(pool=pool, db_session_factory=session_factory)

    # Create FastMCP and register tools
    mcp = FastMCP(name="shuttle")

    @asynccontextmanager
    async def db_session_ctx():
        async with session_factory() as s:
            yield s

    register_tools(
        mcp=mcp,
        pool=pool,
        guard=guard,
        token_store=token_store,
        session_mgr=session_mgr,
        db_session_factory=db_session_ctx,
        node_repo_factory=lambda s: NodeRepo(s),
    )

    return mcp
```

- [ ] **Step 4: Update src/shuttle/mcp/__init__.py**

```python
"""Shuttle MCP server."""

from .server import create_mcp_server

__all__ = ["create_mcp_server"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_mcp/test_server.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/shuttle/mcp/ tests/test_mcp/test_server.py
git commit -m "feat: add MCP server orchestration with DB init, pool setup, and tool registration"
```

---

### Task 11: CLI & Entry Point

**Files:**
- Create: `src/shuttle/cli.py`
- Modify: `src/shuttle/__init__.py`

- [ ] **Step 1: Write src/shuttle/cli.py**

```python
"""Shuttle CLI — Typer application."""

import asyncio
import sys
from pathlib import Path
from typing import Annotated

import typer

from shuttle import __version__
from shuttle.core.config import ShuttleConfig

app = typer.Typer(
    name="shuttle",
    help="Shuttle — Secure SSH gateway for AI assistants",
    add_completion=False,
)

node_app = typer.Typer(help="Manage SSH nodes")
config_app = typer.Typer(help="Manage Shuttle configuration")
app.add_typer(node_app, name="node")
app.add_typer(config_app, name="config")


def _version_callback(value: bool):
    if value:
        typer.echo(f"Shuttle v{__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[bool | None, typer.Option("--version", callback=_version_callback, is_eager=True)] = None,
):
    """Start MCP server (default behavior when no subcommand)."""
    if ctx.invoked_subcommand is None:
        _start_mcp()


def _start_mcp():
    """Start the MCP server in stdio mode."""
    async def _run():
        from shuttle.mcp.server import create_mcp_server
        mcp = await create_mcp_server()
        await mcp.run_async()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass


@app.command()
def web(
    port: Annotated[int, typer.Option(help="Web panel port")] = 9876,
    host: Annotated[str, typer.Option(help="Bind host")] = "127.0.0.1",
):
    """Start the Shuttle web control panel."""
    if host != "127.0.0.1":
        typer.echo(
            "WARNING: Binding to non-loopback interface exposes the API to the network.\n"
            "Ensure you understand the security implications.",
            err=True,
        )

    config = ShuttleConfig()
    token_file = config.shuttle_dir / "web_token"
    if token_file.exists():
        token = token_file.read_text().strip()
    else:
        import secrets
        token = secrets.token_urlsafe(32)
        config.shuttle_dir.mkdir(parents=True, exist_ok=True)
        token_file.write_text(token)
        import os, stat
        os.chmod(token_file, stat.S_IRUSR | stat.S_IWUSR)

    typer.echo(f"Shuttle Web Panel starting at http://{host}:{port}")
    typer.echo(f"Auth token: {token}")
    typer.echo("(Web panel implementation coming in Plan 2)")


# --- Node commands ---

@node_app.command("add")
def node_add(
    name: Annotated[str, typer.Option(prompt=True, help="Node display name")],
    host_addr: Annotated[str, typer.Option("--host", prompt=True, help="SSH hostname")],
    user: Annotated[str, typer.Option("--user", prompt=True, help="SSH username")],
    port: Annotated[int, typer.Option(help="SSH port")] = 22,
    password: Annotated[str | None, typer.Option(help="SSH password")] = None,
    key: Annotated[str | None, typer.Option("--key", help="SSH private key path")] = None,
):
    """Add a new SSH node."""
    if not password and not key:
        password = typer.prompt("Password", hide_input=True)

    async def _add():
        from shuttle.core.config import ShuttleConfig
        from shuttle.core.credentials import CredentialManager
        from shuttle.db.engine import create_db_engine, create_session_factory, init_db
        from shuttle.db.repository import NodeRepo

        config = ShuttleConfig()
        engine = create_db_engine(config.db_url)
        await init_db(engine)
        sf = create_session_factory(engine)
        cred_mgr = CredentialManager(config.shuttle_dir)

        auth_type = "key" if key else "password"
        credential = key if key else password
        encrypted = cred_mgr.encrypt(credential)

        async with sf() as session:
            repo = NodeRepo(session)
            existing = await repo.get_by_name(name)
            if existing:
                typer.echo(f"Node '{name}' already exists.")
                raise typer.Exit(1)
            await repo.create(
                name=name, host=host_addr, port=port, username=user,
                auth_type=auth_type, encrypted_credential=encrypted,
            )
        typer.echo(f"Node '{name}' added ({user}@{host_addr}:{port})")
        await engine.dispose()

    asyncio.run(_add())


@node_app.command("list")
def node_list():
    """List all SSH nodes."""
    async def _list():
        from shuttle.core.config import ShuttleConfig
        from shuttle.db.engine import create_db_engine, create_session_factory, init_db
        from shuttle.db.repository import NodeRepo

        config = ShuttleConfig()
        engine = create_db_engine(config.db_url)
        await init_db(engine)
        sf = create_session_factory(engine)
        async with sf() as session:
            repo = NodeRepo(session)
            nodes = await repo.list_all()
        if not nodes:
            typer.echo("No nodes configured. Use 'shuttle node add' to add one.")
        else:
            for n in nodes:
                icon = {"online": "+", "offline": "x"}.get(n.status, "?")
                typer.echo(f"  [{icon}] {n.name} — {n.username}@{n.host}:{n.port}")
        await engine.dispose()

    asyncio.run(_list())


@node_app.command("remove")
def node_remove(name: Annotated[str, typer.Argument(help="Node name to remove")]):
    """Remove an SSH node."""
    async def _remove():
        from shuttle.core.config import ShuttleConfig
        from shuttle.db.engine import create_db_engine, create_session_factory, init_db
        from shuttle.db.repository import NodeRepo

        config = ShuttleConfig()
        engine = create_db_engine(config.db_url)
        await init_db(engine)
        sf = create_session_factory(engine)
        async with sf() as session:
            repo = NodeRepo(session)
            node = await repo.get_by_name(name)
            if not node:
                typer.echo(f"Node '{name}' not found.")
                raise typer.Exit(1)
            await repo.delete(node.id)
        typer.echo(f"Node '{name}' removed.")
        await engine.dispose()

    asyncio.run(_remove())


@node_app.command("edit")
def node_edit(name: Annotated[str, typer.Argument(help="Node name to edit")]):
    """Edit an SSH node (interactive)."""
    async def _edit():
        from shuttle.core.config import ShuttleConfig
        from shuttle.core.credentials import CredentialManager
        from shuttle.db.engine import create_db_engine, create_session_factory, init_db
        from shuttle.db.repository import NodeRepo

        config = ShuttleConfig()
        engine = create_db_engine(config.db_url)
        await init_db(engine)
        sf = create_session_factory(engine)
        cred_mgr = CredentialManager(config.shuttle_dir)

        async with sf() as session:
            repo = NodeRepo(session)
            node = await repo.get_by_name(name)
            if not node:
                typer.echo(f"Node '{name}' not found.")
                raise typer.Exit(1)

            new_host = typer.prompt("Host", default=node.host)
            new_port = typer.prompt("Port", default=str(node.port), type=int)
            new_user = typer.prompt("Username", default=node.username)

            updates = {"host": new_host, "port": new_port, "username": new_user}
            if typer.confirm("Update credentials?", default=False):
                password = typer.prompt("New password", hide_input=True, default="")
                if password:
                    updates["auth_type"] = "password"
                    updates["encrypted_credential"] = cred_mgr.encrypt(password)

            await repo.update(node.id, **updates)
        typer.echo(f"Node '{name}' updated.")
        await engine.dispose()

    asyncio.run(_edit())


@node_app.command("test")
def node_test(name: Annotated[str, typer.Argument(help="Node name to test")]):
    """Test SSH connectivity to a node."""
    async def _test():
        from shuttle.core.config import ShuttleConfig
        from shuttle.core.credentials import CredentialManager
        from shuttle.core.proxy import NodeConnectInfo, connect_ssh
        from shuttle.db.engine import create_db_engine, create_session_factory, init_db
        from shuttle.db.repository import NodeRepo

        config = ShuttleConfig()
        engine = create_db_engine(config.db_url)
        await init_db(engine)
        sf = create_session_factory(engine)
        cred_mgr = CredentialManager(config.shuttle_dir)

        async with sf() as session:
            repo = NodeRepo(session)
            node = await repo.get_by_name(name)
            if not node:
                typer.echo(f"Node '{name}' not found.")
                raise typer.Exit(1)

            try:
                credential = cred_mgr.decrypt(node.encrypted_credential)
                info = NodeConnectInfo(
                    host=node.host, port=node.port, username=node.username,
                    password=credential if node.auth_type == "password" else None,
                    private_key_path=credential if node.auth_type == "key" else None,
                )
                conn = await connect_ssh(info)
                result = await conn.run("echo ok")
                conn.close()
                await repo.update(node.id, status="online")
                typer.echo(f"Node '{name}' is reachable.")
            except Exception as e:
                await repo.update(node.id, status="offline")
                typer.echo(f"Node '{name}' connection failed: {e}")
                raise typer.Exit(1)
        await engine.dispose()

    asyncio.run(_test())


# --- Config commands ---

@config_app.command("show")
def config_show():
    """Show current Shuttle configuration."""
    config = ShuttleConfig()
    typer.echo(f"Shuttle v{__version__}")
    typer.echo(f"Data directory: {config.shuttle_dir}")
    typer.echo(f"Database: {config.db_url or f'sqlite:///{config.shuttle_dir / \"shuttle.db\"}'}")
    typer.echo(f"Web: {config.web_host}:{config.web_port}")
    typer.echo(f"Pool: max_total={config.pool_max_total} max_per_node={config.pool_max_per_node}")
```

- [ ] **Step 2: Verify CLI works**

```bash
uv run shuttle --version
```

Expected: `Shuttle v0.1.0`

```bash
uv run shuttle config show
```

Expected: Shows config (data dir, DB, pool settings)

- [ ] **Step 3: Commit**

```bash
git add src/shuttle/cli.py
git commit -m "feat: add Typer CLI with shuttle, shuttle web, shuttle node, shuttle config commands"
```

---

### Task 12: Default Security Rules Seeding

**Files:**
- Create: `src/shuttle/db/seeds.py`

- [ ] **Step 1: Write src/shuttle/db/seeds.py**

```python
"""Default security rule seeds."""

DEFAULT_SECURITY_RULES = [
    # Block — always reject, no bypass
    {"pattern": r"^rm -rf /$", "level": "block", "description": "Remove root filesystem", "priority": 1},
    {"pattern": r"mkfs\.", "level": "block", "description": "Format filesystem", "priority": 2},
    {"pattern": r"dd if=.* of=/dev/", "level": "block", "description": "Raw disk write", "priority": 3},
    {"pattern": r":\(\)\{.*:\|:&\};:", "level": "block", "description": "Fork bomb", "priority": 4},

    # Confirm — require confirmation, supports bypass
    {"pattern": r"sudo .*", "level": "confirm", "description": "Sudo commands", "priority": 10},
    {"pattern": r"rm -rf ", "level": "confirm", "description": "Recursive force delete", "priority": 11},
    {"pattern": r"chmod 777", "level": "confirm", "description": "World-writable permissions", "priority": 12},
    {"pattern": r"shutdown", "level": "confirm", "description": "System shutdown", "priority": 13},
    {"pattern": r"reboot", "level": "confirm", "description": "System reboot", "priority": 14},
    {"pattern": r"kill -9", "level": "confirm", "description": "Force kill process", "priority": 15},

    # Warn — log warning, proceed
    {"pattern": r"apt install", "level": "warn", "description": "APT package install", "priority": 20},
    {"pattern": r"pip install", "level": "warn", "description": "Pip package install", "priority": 21},
    {"pattern": r"npm install", "level": "warn", "description": "NPM package install", "priority": 22},
    {"pattern": r"curl .* \| bash", "level": "warn", "description": "Piped remote script", "priority": 23},
]


async def seed_default_rules(session) -> int:
    """Insert default security rules if none exist. Returns count of rules seeded."""
    from shuttle.db.repository import RuleRepo
    repo = RuleRepo(session)
    existing = await repo.list_all()
    if existing:
        return 0  # Don't overwrite user rules

    count = 0
    for rule_data in DEFAULT_SECURITY_RULES:
        await repo.create(**rule_data)
        count += 1
    return count
```

- [ ] **Step 2: Wire seeding into MCP server startup**

Add to `src/shuttle/mcp/server.py`, after `await init_db(engine)`:

```python
from shuttle.db.seeds import seed_default_rules

async with session_factory() as db_session:
    seeded = await seed_default_rules(db_session)
```

- [ ] **Step 3: Commit**

```bash
git add src/shuttle/db/seeds.py src/shuttle/mcp/server.py
git commit -m "feat: add default security rule seeding on first startup"
```

---

### Task 13: Integration Test — Full MCP Flow

**Files:**
- Create: `tests/test_mcp/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
"""Integration test — full MCP server creation and tool invocation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shuttle.mcp.server import create_mcp_server


@pytest.mark.asyncio
async def test_mcp_server_starts_and_lists_nodes(tmp_shuttle_dir):
    """Full integration: create server → invoke ssh_list_nodes → get onboarding message."""
    db_url = f"sqlite+aiosqlite:///{tmp_shuttle_dir / 'test.db'}"

    mcp = await create_mcp_server(shuttle_dir=tmp_shuttle_dir, db_url=db_url)

    # Invoke the list_nodes tool
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    assert "ssh_list_nodes" in tool_names
    assert "ssh_execute" in tool_names
    assert "ssh_session_start" in tool_names

    # Call ssh_list_nodes — should return onboarding message since no nodes configured
    result = await mcp.call_tool("ssh_list_nodes", {})
    # Result is a list of TextContent
    text = result[0].text if result else ""
    assert "No SSH nodes" in text or "no" in text.lower()


@pytest.mark.asyncio
async def test_default_security_rules_seeded(tmp_shuttle_dir):
    """Verify default security rules are created on first startup."""
    db_url = f"sqlite+aiosqlite:///{tmp_shuttle_dir / 'test.db'}"

    from shuttle.db.engine import create_db_engine, create_session_factory, init_db
    from shuttle.db.repository import RuleRepo

    mcp = await create_mcp_server(shuttle_dir=tmp_shuttle_dir, db_url=db_url)

    engine = create_db_engine(db_url)
    sf = create_session_factory(engine)
    async with sf() as session:
        repo = RuleRepo(session)
        rules = await repo.list_all()
        assert len(rules) >= 10  # Should have default rules seeded
        levels = {r.level for r in rules}
        assert "block" in levels
        assert "confirm" in levels
        assert "warn" in levels
    await engine.dispose()
```

- [ ] **Step 2: Run integration test**

Run: `uv run pytest tests/test_mcp/test_integration.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_mcp/test_integration.py
git commit -m "test: add MCP server integration tests"
```

---

### Task 14: Run Full Test Suite & Cleanup

- [ ] **Step 1: Run all tests**

```bash
uv run pytest tests/ -v --tb=short
```

Expected: All tests pass.

- [ ] **Step 2: Run linter**

```bash
uv run ruff check src/shuttle/ tests/
```

Fix any linting issues.

- [ ] **Step 3: Verify CLI end-to-end**

```bash
uv run shuttle --version
uv run shuttle config show
uv run shuttle node list
```

Expected: All commands work without errors.

- [ ] **Step 4: Update .gitignore if needed**

Ensure `.gitignore` has entries for:
```
__pycache__/
*.egg-info/
.shuttle/
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: cleanup and verify full test suite passes"
```

---

## Summary

| Task | Component | Files | Tests |
|------|-----------|-------|-------|
| 1 | Project Scaffold | pyproject.toml, __init__, __main__, conftest | — |
| 2 | DB Models | db/models.py | 5 tests |
| 3 | DB Engine | db/engine.py | (existing pass) |
| 4 | Repository | db/repository.py | 6 tests |
| 5 | Config & Credentials | core/config.py, core/credentials.py | 6 tests |
| 6 | Command Security | core/security.py | 12 tests |
| 7 | Connection Pool | core/connection_pool.py, core/proxy.py | 5 tests |
| 8 | Session Manager | core/session.py | 3 tests |
| 9 | MCP Tools | mcp/tools.py | 3 tests |
| 10 | MCP Server | mcp/server.py | 1 test |
| 11 | CLI | cli.py | (manual verify) |
| 12 | Security Seeds | db/seeds.py | (via integration) |
| 13 | Integration Test | test_integration.py | 2 tests |
| 14 | Cleanup | — | Full suite |

**Total: ~43 tests across 14 tasks.**

After completion: `uvx shuttle` will start a functional MCP server that AI clients can connect to. Plan 2 (Web Panel) adds the React + FastAPI control panel on top.
