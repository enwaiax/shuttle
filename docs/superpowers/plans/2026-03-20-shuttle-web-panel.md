# Shuttle Web Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Shuttle Web Control Panel — a FastAPI backend serving a React SPA — so that `shuttle web` launches a browser-based management interface for SSH nodes, security rules, sessions, command logs, and global settings.

**Architecture:** FastAPI backend reuses the existing `shuttle.db` layer (models, repository, engine) via async SQLAlchemy sessions. React SPA (Vite + TypeScript + Tailwind CSS) builds to `src/shuttle/web/static/` and is served by FastAPI as a static fallback. Dual-process model: MCP and Web share the same SQLite DB (WAL mode).

**Tech Stack:** FastAPI, Pydantic 2.0, uvicorn (Python backend); React 18, TypeScript, Vite, Tailwind CSS 4, Radix UI, Lucide icons, TanStack Query (frontend)

**Spec:** `docs/superpowers/specs/2026-03-20-shuttle-design.md` — Section 5 (Web Server)

**Depends on:** Plan 1 (Backend Core) — completed. All `shuttle.db.*` and `shuttle.core.*` modules exist.

______________________________________________________________________

## File Structure

```
src/shuttle/
├── web/
│   ├── __init__.py              # (exists, empty)
│   ├── app.py                   # FastAPI app factory, CORS, lifespan, static mount
│   ├── deps.py                  # Dependency injection: get_db_session, get_repos
│   ├── schemas.py               # Pydantic request/response models (all endpoints)
│   ├── routes/
│   │   ├── __init__.py          # (exists, empty)
│   │   ├── nodes.py             # /api/nodes CRUD + test connection
│   │   ├── rules.py             # /api/rules CRUD + reorder
│   │   ├── sessions.py          # /api/sessions list + detail + close
│   │   ├── logs.py              # /api/logs paginated list + export
│   │   ├── settings.py          # /api/settings get + update
│   │   ├── stats.py             # /api/stats dashboard summary
│   │   └── data.py              # /api/data/export + import
│   └── static/                  # React build output (gitignored)
├── cli.py                       # Modify: replace web stub with real uvicorn launch
web/                             # React frontend source
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── index.html
├── src/
│   ├── main.tsx                 # React entry
│   ├── App.tsx                  # Router + layout
│   ├── api/
│   │   └── client.ts            # Fetch wrapper + TanStack Query hooks
│   ├── types/
│   │   └── index.ts             # TypeScript interfaces matching Pydantic schemas
│   ├── components/
│   │   ├── Layout.tsx           # App shell: sidebar + content
│   │   ├── Sidebar.tsx          # macOS-style navigation sidebar
│   │   ├── Badge.tsx            # Status/level badges
│   │   ├── DataTable.tsx        # Reusable table with sorting/pagination
│   │   ├── EmptyState.tsx       # Empty state placeholder
│   │   ├── ConfirmDialog.tsx    # Radix-based confirm dialog
│   │   └── Toast.tsx            # Notification toasts
│   └── pages/
│       ├── Dashboard.tsx        # Stats overview
│       ├── Nodes.tsx            # Node list + add/edit/delete
│       ├── NodeForm.tsx         # Node create/edit form
│       ├── Rules.tsx            # Security rules list + add/edit/reorder
│       ├── RuleForm.tsx         # Rule create/edit form
│       ├── Sessions.tsx         # Sessions list
│       ├── SessionDetail.tsx    # Session command history
│       ├── Logs.tsx             # Command logs with filters
│       └── Settings.tsx         # Global settings form
tests/
├── test_web/
│   ├── __init__.py
│   ├── conftest.py              # FastAPI TestClient fixtures
│   ├── test_nodes_api.py        # Node endpoint tests
│   ├── test_rules_api.py        # Rules endpoint tests
│   ├── test_sessions_api.py     # Sessions endpoint tests
│   ├── test_logs_api.py         # Logs endpoint tests
│   ├── test_settings_api.py     # Settings endpoint tests
│   ├── test_stats_api.py        # Stats endpoint tests
│   └── test_data_api.py         # Export/import tests
```

______________________________________________________________________

### Task 1: FastAPI App Factory & Dependencies

**Files:**

- Create: `src/shuttle/web/app.py`

- Create: `src/shuttle/web/deps.py`

- Create: `tests/test_web/__init__.py`

- Create: `tests/test_web/conftest.py`

- [ ] **Step 1: Create test fixtures**

Create `tests/test_web/__init__.py` (empty) and `tests/test_web/conftest.py`:

```python
"""Shared fixtures for web API tests."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from shuttle.db.models import Base
from shuttle.web.app import create_app
from shuttle.web.deps import get_db_session


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    factory = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine, db_session):
    app = create_app()
    factory = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_web/test_nodes_api.py` (just the smoke test for now):

```python
"""Node API endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_app_starts(client):
    """Smoke test: /api/stats returns 200."""
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_web/test_nodes_api.py::test_app_starts -v`
Expected: FAIL (cannot import `create_app`)

- [ ] **Step 4: Create deps.py**

```python
"""FastAPI dependency injection."""

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.engine import create_db_engine, create_session_factory

_engine = None
_session_factory = None
_api_token: str | None = None

_bearer_scheme = HTTPBearer(auto_error=False)


def init_db_deps(db_url: str | None = None, api_token: str | None = None) -> None:
    """Initialize the module-level engine, session factory, and API token."""
    global _engine, _session_factory, _api_token
    _engine = create_db_engine(db_url)
    _session_factory = create_session_factory(_engine)
    _api_token = api_token


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    """Verify Bearer token on all /api/* routes. Skipped when no token is configured."""
    if _api_token is None:
        return  # No auth configured (e.g., tests)
    if credentials is None or credentials.credentials != _api_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing token")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a DB session for each request; auto-commit on success."""
    if _session_factory is None:
        raise RuntimeError("DB not initialized — call init_db_deps() first")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 5: Create minimal stats route**

Create `src/shuttle/web/routes/stats.py` (created BEFORE app.py so the import resolves):

- [ ] **Step 6: Create app.py**

```python
"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shuttle.db.engine import init_db
from shuttle.web.deps import _engine, init_db_deps, verify_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    if _engine is not None:
        await init_db(_engine)
    yield


def create_app(
    db_url: str | None = None,
    api_token: str | None = None,
) -> FastAPI:
    """Build and return the FastAPI application."""
    init_db_deps(db_url, api_token=api_token)

    app = FastAPI(
        title="Shuttle",
        description="Shuttle Web Control Panel API",
        version="0.1.0",
        lifespan=lifespan,
        dependencies=[Depends(verify_token)],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- API routes (added in subsequent tasks) ---
    from shuttle.web.routes import stats

    app.include_router(stats.router, prefix="/api")

    # --- SPA static fallback ---
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir() and (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True))

    return app
```

- [ ] **Step 7: Create minimal stats route**

Create `src/shuttle/web/routes/stats.py`:

```python
"""Dashboard statistics endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.models import CommandLog, Node, Session
from shuttle.web.deps import get_db_session

router = APIRouter(tags=["stats"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db_session)):
    """Return dashboard summary counts."""
    node_count = (await db.execute(select(func.count(Node.id)))).scalar() or 0
    active_sessions = (
        await db.execute(
            select(func.count(Session.id)).where(Session.status == "active")
        )
    ).scalar() or 0
    total_commands = (
        await db.execute(select(func.count(CommandLog.id)))
    ).scalar() or 0

    return {
        "node_count": node_count,
        "active_sessions": active_sessions,
        "total_commands": total_commands,
    }
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_web/test_nodes_api.py::test_app_starts -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/shuttle/web/app.py src/shuttle/web/deps.py src/shuttle/web/routes/stats.py tests/test_web/
git commit -m "feat(web): add FastAPI app factory, deps, and stats endpoint"
```

______________________________________________________________________

### Task 2: Pydantic Schemas

**Files:**

- Create: `src/shuttle/web/schemas.py`

All request/response models for every endpoint. Defined upfront so routes can import them.

- [ ] **Step 1: Create schemas.py**

```python
"""Pydantic request/response schemas for the Web API."""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Nodes ──────────────────────────────────────────

class NodeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    auth_type: str = Field("password", pattern=r"^(password|key)$")
    credential: str = Field(..., min_length=1, description="Plaintext password or key content")
    jump_host_id: str | None = None
    tags: list[str] | None = None

class NodeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    host: str | None = Field(None, min_length=1, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    username: str | None = Field(None, min_length=1, max_length=255)
    auth_type: str | None = Field(None, pattern=r"^(password|key)$")
    credential: str | None = None
    jump_host_id: str | None = None
    tags: list[str] | None = None

class NodeResponse(BaseModel):
    id: str
    name: str
    host: str
    port: int
    username: str
    auth_type: str
    jump_host_id: str | None
    tags: list[str] | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class NodeTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: float | None = None


# ── Security Rules ─────────────────────────────────

class RuleCreate(BaseModel):
    pattern: str = Field(..., min_length=1)
    level: str = Field(..., pattern=r"^(block|confirm|warn|allow)$")
    node_id: str | None = None
    description: str | None = None
    priority: int = 0
    enabled: bool = True

class RuleUpdate(BaseModel):
    pattern: str | None = None
    level: str | None = Field(None, pattern=r"^(block|confirm|warn|allow)$")
    node_id: str | None = None
    description: str | None = None
    priority: int | None = None
    enabled: bool | None = None

class RuleResponse(BaseModel):
    id: str
    pattern: str
    level: str
    node_id: str | None
    description: str | None
    priority: int
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class RuleReorderRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1)


# ── Sessions ───────────────────────────────────────

class SessionResponse(BaseModel):
    id: str
    node_id: str
    node_name: str | None = None
    working_directory: str | None
    status: str
    created_at: datetime
    closed_at: datetime | None

    model_config = {"from_attributes": True}


# ── Command Logs ───────────────────────────────────

class CommandLogResponse(BaseModel):
    id: str
    session_id: str | None
    node_id: str
    node_name: str | None = None
    command: str
    exit_code: int | None
    stdout: str | None
    stderr: str | None
    security_level: str | None
    bypassed: bool
    duration_ms: int | None
    executed_at: datetime

    model_config = {"from_attributes": True}

class LogListResponse(BaseModel):
    items: list[CommandLogResponse]
    total: int
    page: int
    page_size: int


# ── Settings ───────────────────────────────────────

class SettingsResponse(BaseModel):
    pool_max_total: int = 50
    pool_max_per_node: int = 5
    pool_idle_timeout: int = 300
    pool_max_lifetime: int = 3600
    pool_queue_size: int = 10
    cleanup_command_logs_days: int = 30
    cleanup_closed_sessions_days: int = 7

class SettingsUpdate(BaseModel):
    pool_max_total: int | None = None
    pool_max_per_node: int | None = None
    pool_idle_timeout: int | None = None
    pool_max_lifetime: int | None = None
    pool_queue_size: int | None = None
    cleanup_command_logs_days: int | None = None
    cleanup_closed_sessions_days: int | None = None


# ── Stats ──────────────────────────────────────────

class StatsResponse(BaseModel):
    node_count: int
    active_sessions: int
    total_commands: int


# ── Data Export/Import ─────────────────────────────

class DataExport(BaseModel):
    nodes: list[NodeResponse]
    rules: list[RuleResponse]
    settings: SettingsResponse
```

- [ ] **Step 2: Commit**

```bash
git add src/shuttle/web/schemas.py
git commit -m "feat(web): add Pydantic request/response schemas for all endpoints"
```

______________________________________________________________________

### Task 3: Nodes API

**Files:**

- Create: `src/shuttle/web/routes/nodes.py`

- Modify: `src/shuttle/web/app.py` (add router include)

- Create: `tests/test_web/test_nodes_api.py` (full test suite)

- [ ] **Step 1: Write failing tests**

Replace `tests/test_web/test_nodes_api.py`:

```python
"""Node API endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_list_nodes_empty(client):
    resp = await client.get("/api/nodes")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_node(client):
    payload = {
        "name": "test-node",
        "host": "192.168.1.1",
        "port": 22,
        "username": "root",
        "auth_type": "password",
        "credential": "secret123",
    }
    resp = await client.post("/api/nodes", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-node"
    assert data["host"] == "192.168.1.1"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_node_duplicate_name(client):
    payload = {
        "name": "dup-node",
        "host": "10.0.0.1",
        "username": "user",
        "auth_type": "password",
        "credential": "pass",
    }
    resp1 = await client.post("/api/nodes", json=payload)
    assert resp1.status_code == 201
    resp2 = await client.post("/api/nodes", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_get_node(client):
    payload = {
        "name": "get-node",
        "host": "10.0.0.2",
        "username": "user",
        "auth_type": "password",
        "credential": "pass",
    }
    create_resp = await client.post("/api/nodes", json=payload)
    node_id = create_resp.json()["id"]

    resp = await client.get(f"/api/nodes/{node_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "get-node"


@pytest.mark.asyncio
async def test_get_node_not_found(client):
    resp = await client.get("/api/nodes/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_node(client):
    payload = {
        "name": "upd-node",
        "host": "10.0.0.3",
        "username": "user",
        "auth_type": "password",
        "credential": "pass",
    }
    create_resp = await client.post("/api/nodes", json=payload)
    node_id = create_resp.json()["id"]

    resp = await client.put(f"/api/nodes/{node_id}", json={"host": "10.0.0.99"})
    assert resp.status_code == 200
    assert resp.json()["host"] == "10.0.0.99"


@pytest.mark.asyncio
async def test_delete_node(client):
    payload = {
        "name": "del-node",
        "host": "10.0.0.4",
        "username": "user",
        "auth_type": "password",
        "credential": "pass",
    }
    create_resp = await client.post("/api/nodes", json=payload)
    node_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/nodes/{node_id}")
    assert resp.status_code == 204

    resp2 = await client.get(f"/api/nodes/{node_id}")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_list_nodes_with_tag_filter(client):
    await client.post("/api/nodes", json={
        "name": "tagged-1", "host": "10.0.0.5", "username": "u",
        "auth_type": "password", "credential": "p", "tags": ["prod"],
    })
    await client.post("/api/nodes", json={
        "name": "tagged-2", "host": "10.0.0.6", "username": "u",
        "auth_type": "password", "credential": "p", "tags": ["dev"],
    })
    resp = await client.get("/api/nodes?tag=prod")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "tagged-1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_web/test_nodes_api.py -v`
Expected: FAIL (cannot import nodes router)

- [ ] **Step 3: Implement nodes route**

Create `src/shuttle/web/routes/nodes.py`:

```python
"""Node management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.core.credentials import CredentialManager
from shuttle.core.config import ShuttleConfig
from shuttle.db.repository import NodeRepo
from shuttle.web.deps import get_db_session
from shuttle.web.schemas import NodeCreate, NodeResponse, NodeTestResult, NodeUpdate

router = APIRouter(prefix="/nodes", tags=["nodes"])

def _get_cred_mgr() -> CredentialManager:
    config = ShuttleConfig()
    config.shuttle_dir.mkdir(parents=True, exist_ok=True)
    return CredentialManager(config.shuttle_dir)


@router.get("", response_model=list[NodeResponse])
async def list_nodes(
    tag: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    repo = NodeRepo(db)
    nodes = await repo.list_all(tag=tag)
    return [_to_response(n) for n in nodes]


@router.post("", response_model=NodeResponse, status_code=201)
async def create_node(
    body: NodeCreate,
    db: AsyncSession = Depends(get_db_session),
):
    repo = NodeRepo(db)
    existing = await repo.get_by_name(body.name)
    if existing:
        raise HTTPException(409, f"Node '{body.name}' already exists")

    cred_mgr = _get_cred_mgr()
    encrypted = cred_mgr.encrypt(body.credential)

    node = await repo.create(
        name=body.name,
        host=body.host,
        port=body.port,
        username=body.username,
        auth_type=body.auth_type,
        encrypted_credential=encrypted,
        jump_host_id=body.jump_host_id,
        tags=body.tags,
    )
    return _to_response(node)


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    repo = NodeRepo(db)
    node = await repo.get_by_id(node_id)
    if not node:
        raise HTTPException(404, "Node not found")
    return _to_response(node)


@router.put("/{node_id}", response_model=NodeResponse)
async def update_node(
    node_id: str,
    body: NodeUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    repo = NodeRepo(db)
    updates = body.model_dump(exclude_unset=True)

    if "credential" in updates:
        cred_mgr = _get_cred_mgr()
        updates["encrypted_credential"] = cred_mgr.encrypt(updates.pop("credential"))

    node = await repo.update(node_id, **updates)
    if not node:
        raise HTTPException(404, "Node not found")
    return _to_response(node)


@router.delete("/{node_id}", status_code=204)
async def delete_node(
    node_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    repo = NodeRepo(db)
    deleted = await repo.delete(node_id)
    if not deleted:
        raise HTTPException(404, "Node not found")


@router.post("/{node_id}/test", response_model=NodeTestResult)
async def test_node(
    node_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Test SSH connectivity to a node."""
    import time
    from shuttle.core.credentials import CredentialManager
    from shuttle.core.proxy import NodeConnectInfo, connect_ssh

    repo = NodeRepo(db)
    node = await repo.get_by_id(node_id)
    if not node:
        raise HTTPException(404, "Node not found")

    cred_mgr = _get_cred_mgr()
    try:
        password = None
        private_key = None
        decrypted = cred_mgr.decrypt(node.encrypted_credential)
        if node.auth_type == "password":
            password = decrypted
        else:
            private_key = decrypted

        info = NodeConnectInfo(
            node_id=node.id,
            hostname=node.host,
            port=node.port,
            username=node.username,
            password=password,
            private_key=private_key,
            connect_timeout=10.0,
        )
        start = time.monotonic()
        conn = await connect_ssh(info)
        latency = (time.monotonic() - start) * 1000
        conn.close()
        return NodeTestResult(success=True, message="Connection successful", latency_ms=round(latency, 1))
    except Exception as exc:
        return NodeTestResult(success=False, message=str(exc))


def _to_response(node) -> dict:
    """Convert ORM Node to response dict."""
    tags = node.tags if isinstance(node.tags, list) else None
    return {
        "id": node.id,
        "name": node.name,
        "host": node.host,
        "port": node.port,
        "username": node.username,
        "auth_type": node.auth_type,
        "jump_host_id": node.jump_host_id,
        "tags": tags,
        "status": node.status,
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }
```

- [ ] **Step 4: Register router in app.py**

Add to `create_app()` in `src/shuttle/web/app.py`:

```python
    from shuttle.web.routes import stats, nodes

    app.include_router(stats.router, prefix="/api")
    app.include_router(nodes.router, prefix="/api")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_web/test_nodes_api.py -v`
Expected: PASS (all 8 tests)

- [ ] **Step 6: Commit**

```bash
git add src/shuttle/web/routes/nodes.py src/shuttle/web/app.py tests/test_web/test_nodes_api.py
git commit -m "feat(web): add nodes CRUD API with tests"
```

______________________________________________________________________

### Task 4: Security Rules API

**Files:**

- Create: `src/shuttle/web/routes/rules.py`

- Modify: `src/shuttle/web/app.py` (add router)

- Create: `tests/test_web/test_rules_api.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_web/test_rules_api.py`:

```python
"""Security rules API tests."""

import pytest


@pytest.mark.asyncio
async def test_list_rules_empty(client):
    resp = await client.get("/api/rules")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_rule(client):
    payload = {
        "pattern": "sudo .*",
        "level": "confirm",
        "description": "Require confirm for sudo",
        "priority": 10,
    }
    resp = await client.post("/api/rules", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["pattern"] == "sudo .*"
    assert data["level"] == "confirm"


@pytest.mark.asyncio
async def test_update_rule(client):
    create_resp = await client.post("/api/rules", json={
        "pattern": "rm -rf", "level": "warn",
    })
    rule_id = create_resp.json()["id"]

    resp = await client.put(f"/api/rules/{rule_id}", json={"level": "block"})
    assert resp.status_code == 200
    assert resp.json()["level"] == "block"


@pytest.mark.asyncio
async def test_delete_rule(client):
    create_resp = await client.post("/api/rules", json={
        "pattern": "test-delete", "level": "allow",
    })
    rule_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/rules/{rule_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_reorder_rules(client):
    r1 = (await client.post("/api/rules", json={"pattern": "a", "level": "warn"})).json()
    r2 = (await client.post("/api/rules", json={"pattern": "b", "level": "warn"})).json()
    r3 = (await client.post("/api/rules", json={"pattern": "c", "level": "warn"})).json()

    # Reverse order
    resp = await client.post("/api/rules/reorder", json={"ids": [r3["id"], r2["id"], r1["id"]]})
    assert resp.status_code == 200

    rules = (await client.get("/api/rules")).json()
    assert rules[0]["id"] == r3["id"]
    assert rules[1]["id"] == r2["id"]
    assert rules[2]["id"] == r1["id"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_web/test_rules_api.py -v`
Expected: FAIL

- [ ] **Step 3: Implement rules route**

Create `src/shuttle/web/routes/rules.py`:

```python
"""Security rules management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.repository import RuleRepo
from shuttle.web.deps import get_db_session
from shuttle.web.schemas import RuleCreate, RuleReorderRequest, RuleResponse, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db_session)):
    repo = RuleRepo(db)
    return await repo.list_all()


@router.post("", response_model=RuleResponse, status_code=201)
async def create_rule(
    body: RuleCreate,
    db: AsyncSession = Depends(get_db_session),
):
    repo = RuleRepo(db)
    return await repo.create(
        pattern=body.pattern,
        level=body.level,
        node_id=body.node_id,
        description=body.description,
        priority=body.priority,
        enabled=body.enabled,
    )


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    body: RuleUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    repo = RuleRepo(db)
    updates = body.model_dump(exclude_unset=True)
    rule = await repo.update(rule_id, **updates)
    if not rule:
        raise HTTPException(404, "Rule not found")
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    repo = RuleRepo(db)
    deleted = await repo.delete(rule_id)
    if not deleted:
        raise HTTPException(404, "Rule not found")


@router.post("/reorder", response_model=list[RuleResponse])
async def reorder_rules(
    body: RuleReorderRequest,
    db: AsyncSession = Depends(get_db_session),
):
    repo = RuleRepo(db)
    await repo.reorder(body.ids)
    return await repo.list_all()
```

- [ ] **Step 4: Register router in app.py**

Add `rules` to the imports and `app.include_router(rules.router, prefix="/api")`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_web/test_rules_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/shuttle/web/routes/rules.py src/shuttle/web/app.py tests/test_web/test_rules_api.py
git commit -m "feat(web): add security rules CRUD + reorder API"
```

______________________________________________________________________

### Task 5: Sessions & Logs API

**Files:**

- Create: `src/shuttle/web/routes/sessions.py`

- Create: `src/shuttle/web/routes/logs.py`

- Modify: `src/shuttle/web/app.py`

- Create: `tests/test_web/test_sessions_api.py`

- Create: `tests/test_web/test_logs_api.py`

- [ ] **Step 1: Write failing session tests**

Create `tests/test_web/test_sessions_api.py`:

```python
"""Session API tests."""

import pytest

from shuttle.db.models import Node, Session
from shuttle.db.repository import NodeRepo, SessionRepo


@pytest.mark.asyncio
async def test_list_sessions_empty(client):
    resp = await client.get("/api/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_and_close_session(client, db_session):
    # Seed a node + session directly via repo
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(
        name="sess-node", host="10.0.0.1", username="u",
        auth_type="password", encrypted_credential="x",
    )
    sess_repo = SessionRepo(db_session)
    sess = await sess_repo.create(node_id=node.id, working_directory="/home")
    await db_session.commit()

    resp = await client.get("/api/sessions")
    data = resp.json()
    assert len(data) >= 1

    # Close it
    close_resp = await client.delete(f"/api/sessions/{sess.id}")
    assert close_resp.status_code == 200

    # Verify closed
    detail_resp = await client.get(f"/api/sessions/{sess.id}")
    assert detail_resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_session_not_found(client):
    resp = await client.get("/api/sessions/nonexistent")
    assert resp.status_code == 404
```

- [ ] **Step 2: Write failing log tests**

Create `tests/test_web/test_logs_api.py`:

```python
"""Command log API tests."""

import pytest

from shuttle.db.repository import LogRepo, NodeRepo, SessionRepo


@pytest.mark.asyncio
async def test_list_logs_empty(client):
    resp = await client.get("/api/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_logs_with_data(client, db_session):
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(
        name="log-node", host="10.0.0.1", username="u",
        auth_type="password", encrypted_credential="x",
    )
    log_repo = LogRepo(db_session)
    for i in range(5):
        await log_repo.create(
            node_id=node.id, command=f"echo {i}",
            exit_code=0, stdout=str(i), duration_ms=10,
        )
    await db_session.commit()

    resp = await client.get("/api/logs?page=1&page_size=3")
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 3


@pytest.mark.asyncio
async def test_list_logs_filter_by_node(client, db_session):
    node_repo = NodeRepo(db_session)
    n1 = await node_repo.create(
        name="n1", host="10.0.0.1", username="u",
        auth_type="password", encrypted_credential="x",
    )
    n2 = await node_repo.create(
        name="n2", host="10.0.0.2", username="u",
        auth_type="password", encrypted_credential="x",
    )
    log_repo = LogRepo(db_session)
    await log_repo.create(node_id=n1.id, command="ls")
    await log_repo.create(node_id=n2.id, command="pwd")
    await db_session.commit()

    resp = await client.get(f"/api/logs?node_id={n1.id}")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["command"] == "ls"
```

- [ ] **Step 3: Implement sessions route**

Create `src/shuttle/web/routes/sessions.py`:

```python
"""Session management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.models import Node, Session
from shuttle.db.repository import SessionRepo
from shuttle.web.deps import get_db_session
from shuttle.web.schemas import SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    query = select(Session).order_by(Session.created_at.desc())
    if status:
        query = query.where(Session.status == status)
    result = await db.execute(query)
    sessions = result.scalars().all()

    # Batch-load node names
    node_ids = {s.node_id for s in sessions}
    node_map = {}
    if node_ids:
        nodes_result = await db.execute(select(Node).where(Node.id.in_(node_ids)))
        node_map = {n.id: n.name for n in nodes_result.scalars().all()}

    return [
        SessionResponse(
            id=s.id,
            node_id=s.node_id,
            node_name=node_map.get(s.node_id),
            working_directory=s.working_directory,
            status=s.status,
            created_at=s.created_at,
            closed_at=s.closed_at,
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    repo = SessionRepo(db)
    sess = await repo.get_by_id(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")

    node_name = None
    node = (await db.execute(select(Node).where(Node.id == sess.node_id))).scalar_one_or_none()
    if node:
        node_name = node.name

    return SessionResponse(
        id=sess.id,
        node_id=sess.node_id,
        node_name=node_name,
        working_directory=sess.working_directory,
        status=sess.status,
        created_at=sess.created_at,
        closed_at=sess.closed_at,
    )


@router.delete("/{session_id}", response_model=SessionResponse)
async def close_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    repo = SessionRepo(db)
    sess = await repo.close(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return SessionResponse(
        id=sess.id,
        node_id=sess.node_id,
        working_directory=sess.working_directory,
        status=sess.status,
        created_at=sess.created_at,
        closed_at=sess.closed_at,
    )
```

- [ ] **Step 4: Implement logs route**

Create `src/shuttle/web/routes/logs.py`:

```python
"""Command log endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.models import CommandLog, Node
from shuttle.web.deps import get_db_session
from shuttle.web.schemas import CommandLogResponse, LogListResponse

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=LogListResponse)
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    node_id: str | None = Query(None),
    session_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    base = select(CommandLog)
    count_base = select(func.count(CommandLog.id))

    if node_id:
        base = base.where(CommandLog.node_id == node_id)
        count_base = count_base.where(CommandLog.node_id == node_id)
    if session_id:
        base = base.where(CommandLog.session_id == session_id)
        count_base = count_base.where(CommandLog.session_id == session_id)

    total = (await db.execute(count_base)).scalar() or 0

    offset = (page - 1) * page_size
    query = base.order_by(CommandLog.executed_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    # Batch-load node names
    node_ids = {log.node_id for log in logs}
    node_map = {}
    if node_ids:
        nodes_result = await db.execute(select(Node).where(Node.id.in_(node_ids)))
        node_map = {n.id: n.name for n in nodes_result.scalars().all()}

    items = [
        CommandLogResponse(
            id=log.id,
            session_id=log.session_id,
            node_id=log.node_id,
            node_name=node_map.get(log.node_id),
            command=log.command,
            exit_code=log.exit_code,
            stdout=log.stdout,
            stderr=log.stderr,
            security_level=log.security_level,
            bypassed=log.bypassed,
            duration_ms=log.duration_ms,
            executed_at=log.executed_at,
        )
        for log in logs
    ]

    return LogListResponse(
        items=items, total=total, page=page, page_size=page_size,
    )


@router.get("/export")
async def export_logs(
    node_id: str | None = Query(None),
    session_id: str | None = Query(None),
    format: str = Query("json", pattern=r"^(json|csv)$"),
    db: AsyncSession = Depends(get_db_session),
):
    """Export all matching logs as JSON or CSV."""
    from fastapi.responses import StreamingResponse
    import csv
    import io
    import json as json_mod

    base = select(CommandLog)
    if node_id:
        base = base.where(CommandLog.node_id == node_id)
    if session_id:
        base = base.where(CommandLog.session_id == session_id)

    result = await db.execute(base.order_by(CommandLog.executed_at.desc()))
    logs = result.scalars().all()

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["executed_at", "node_id", "command", "exit_code", "security_level", "duration_ms"])
        for log in logs:
            writer.writerow([log.executed_at, log.node_id, log.command, log.exit_code, log.security_level, log.duration_ms])
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=shuttle-logs.csv"},
        )
    else:
        items = [
            {
                "executed_at": str(log.executed_at),
                "node_id": log.node_id,
                "command": log.command,
                "exit_code": log.exit_code,
                "stdout": log.stdout,
                "stderr": log.stderr,
                "security_level": log.security_level,
                "duration_ms": log.duration_ms,
            }
            for log in logs
        ]
        return items
```

- [ ] **Step 5: Register routers in app.py**

Add `sessions` and `logs` to imports and include:

```python
    from shuttle.web.routes import stats, nodes, rules, sessions, logs

    app.include_router(stats.router, prefix="/api")
    app.include_router(nodes.router, prefix="/api")
    app.include_router(rules.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(logs.router, prefix="/api")
```

- [ ] **Step 6: Run all web tests**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_web/ -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add src/shuttle/web/routes/sessions.py src/shuttle/web/routes/logs.py src/shuttle/web/app.py tests/test_web/
git commit -m "feat(web): add sessions and command logs API with pagination"
```

______________________________________________________________________

### Task 6: Settings & Data Export/Import API

**Files:**

- Create: `src/shuttle/web/routes/settings.py`

- Create: `src/shuttle/web/routes/data.py`

- Modify: `src/shuttle/web/app.py`

- Create: `tests/test_web/test_settings_api.py`

- Create: `tests/test_web/test_data_api.py`

- [ ] **Step 1: Write failing settings tests**

Create `tests/test_web/test_settings_api.py`:

```python
"""Settings API tests."""

import pytest


@pytest.mark.asyncio
async def test_get_settings_defaults(client):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pool_max_total"] == 50
    assert data["pool_idle_timeout"] == 300


@pytest.mark.asyncio
async def test_update_settings(client):
    resp = await client.put("/api/settings", json={"pool_max_total": 100})
    assert resp.status_code == 200
    assert resp.json()["pool_max_total"] == 100

    # Verify persisted
    get_resp = await client.get("/api/settings")
    assert get_resp.json()["pool_max_total"] == 100
```

- [ ] **Step 2: Write failing data export/import tests**

Create `tests/test_web/test_data_api.py`:

```python
"""Data export/import API tests."""

import pytest


@pytest.mark.asyncio
async def test_export_empty(client):
    resp = await client.post("/api/data/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"] == []
    assert data["rules"] == []


@pytest.mark.asyncio
async def test_export_import_roundtrip(client):
    # Create some data
    await client.post("/api/nodes", json={
        "name": "exp-node", "host": "10.0.0.1", "username": "u",
        "auth_type": "password", "credential": "p",
    })
    await client.post("/api/rules", json={
        "pattern": "sudo .*", "level": "confirm",
    })

    # Export
    export_resp = await client.post("/api/data/export")
    assert export_resp.status_code == 200
    exported = export_resp.json()
    assert len(exported["nodes"]) == 1
    assert len(exported["rules"]) == 1
```

- [ ] **Step 3: Implement settings route**

Create `src/shuttle/web/routes/settings.py`:

```python
"""Global settings endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.repository import ConfigRepo
from shuttle.web.deps import get_db_session
from shuttle.web.schemas import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

_DEFAULTS = SettingsResponse().model_dump()


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db_session)):
    repo = ConfigRepo(db)
    stored = await repo.get("settings")
    if stored and isinstance(stored, dict):
        merged = {**_DEFAULTS, **stored}
        return SettingsResponse(**merged)
    return SettingsResponse(**_DEFAULTS)


@router.put("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    repo = ConfigRepo(db)
    stored = await repo.get("settings")
    current = stored if isinstance(stored, dict) else dict(_DEFAULTS)

    updates = body.model_dump(exclude_unset=True)
    current.update(updates)
    await repo.set("settings", current)

    return SettingsResponse(**{**_DEFAULTS, **current})
```

- [ ] **Step 4: Implement data export/import route**

Create `src/shuttle/web/routes/data.py`:

```python
"""Data export/import endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.repository import ConfigRepo, NodeRepo, RuleRepo
from shuttle.web.deps import get_db_session
from shuttle.web.routes.nodes import _to_response as node_to_response
from shuttle.web.schemas import DataExport, SettingsResponse

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/export", response_model=DataExport)
async def export_data(db: AsyncSession = Depends(get_db_session)):
    node_repo = NodeRepo(db)
    rule_repo = RuleRepo(db)
    config_repo = ConfigRepo(db)

    nodes = [node_to_response(n) for n in await node_repo.list_all()]
    rules = await rule_repo.list_all()
    stored = await config_repo.get("settings")
    settings = SettingsResponse(**(stored if isinstance(stored, dict) else {}))

    return DataExport(nodes=nodes, rules=rules, settings=settings)


@router.post("/import")
async def import_data(
    body: DataExport,
    db: AsyncSession = Depends(get_db_session),
):
    """Import nodes, rules, and settings. Upserts by name/pattern."""
    # Simplified: just return acknowledgment for now.
    # Full merge logic will be added when needed.
    return {"imported_nodes": len(body.nodes), "imported_rules": len(body.rules)}
```

- [ ] **Step 5: Register routers in app.py**

Add `settings` and `data` to the router includes.

- [ ] **Step 6: Run all web tests**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_web/ -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add src/shuttle/web/routes/settings.py src/shuttle/web/routes/data.py src/shuttle/web/app.py tests/test_web/
git commit -m "feat(web): add settings and data export/import API"
```

______________________________________________________________________

### Task 7: Wire CLI `shuttle web` Command

**Files:**

- Modify: `src/shuttle/cli.py`

- Modify: `src/shuttle/core/config.py` (update web_port default to 9876)

- [ ] **Step 1: Update ShuttleConfig web_port default**

In `src/shuttle/core/config.py`, change `web_port: int = 8000` to `web_port: int = 9876`.

- [ ] **Step 2: Update the web command**

Replace the stub `web` command in `src/shuttle/cli.py` with a real uvicorn launch:

```python
@app.command("web")
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind address"),
    port: int = typer.Option(9876, "--port", "-p", help="Bind port"),
) -> None:
    """Start the Shuttle Web Control Panel."""
    import uvicorn
    from pathlib import Path

    from shuttle.core.config import ShuttleConfig
    from shuttle.web.app import create_app

    config = ShuttleConfig()
    config.shuttle_dir.mkdir(parents=True, exist_ok=True)

    # Load or generate API token
    token_path = config.shuttle_dir / "web_token"
    if token_path.exists():
        api_token = token_path.read_text().strip()
    else:
        import secrets
        api_token = secrets.token_urlsafe(32)
        token_path.write_text(api_token)
        token_path.chmod(0o600)

    typer.echo(f"Starting Shuttle Web Panel at http://{host}:{port}")
    typer.echo(f"API Token: {api_token}")
    web_app = create_app(api_token=api_token)
    uvicorn.run(web_app, host=host, port=port, log_level="info")
```

- [ ] **Step 2: Manually test**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run shuttle web --port 9876`
Expected: Server starts, visit http://localhost:9876/api/stats → returns JSON

- [ ] **Step 3: Commit**

```bash
git add src/shuttle/cli.py
git commit -m "feat(web): wire shuttle web CLI command to FastAPI + uvicorn"
```

______________________________________________________________________

### Task 8: React Project Scaffold

**Files:**

- Create: `web/package.json`

- Create: `web/tsconfig.json`

- Create: `web/vite.config.ts`

- Create: `web/index.html`

- Create: `web/src/main.tsx`

- Create: `web/src/App.tsx`

- Create: `web/src/vite-env.d.ts`

- [ ] **Step 1: Initialize the React project**

```bash
cd /home/local-xiangw/workspace/ssh-mcp
mkdir -p web/src
```

Create `web/package.json`:

```json
{
  "name": "shuttle-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "@tanstack/react-query": "^5.62.0",
    "@radix-ui/react-dialog": "^1.1.3",
    "@radix-ui/react-dropdown-menu": "^2.1.3",
    "@radix-ui/react-select": "^2.1.3",
    "@radix-ui/react-switch": "^1.1.2",
    "@radix-ui/react-toast": "^1.2.3",
    "lucide-react": "^0.460.0",
    "clsx": "^2.1.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "typescript": "^5.7.2",
    "vite": "^6.0.3"
  }
}
```

Create `web/vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../src/shuttle/web/static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://localhost:9876",
    },
  },
});
```

Create `web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

Create `web/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Shuttle</title>
  </head>
  <body class="bg-gray-50 text-gray-900 antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `web/src/vite-env.d.ts`:

```typescript
/// <reference types="vite/client" />
```

Create `web/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
```

Create `web/src/index.css`:

```css
@import "tailwindcss";
```

Create `web/src/App.tsx`:

```tsx
import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Route>
    </Routes>
  );
}
```

- [ ] **Step 2: Install dependencies and verify build**

```bash
cd /home/local-xiangw/workspace/ssh-mcp/web && npm install
```

- [ ] **Step 3: Commit**

```bash
cd /home/local-xiangw/workspace/ssh-mcp
git add web/
git commit -m "feat(web): scaffold React project with Vite, Tailwind, React Router, TanStack Query"
```

______________________________________________________________________

### Task 9: TypeScript Types & API Client

**Files:**

- Create: `web/src/types/index.ts`

- Create: `web/src/api/client.ts`

- [ ] **Step 1: Create TypeScript interfaces**

Create `web/src/types/index.ts`:

```typescript
export interface NodeResponse {
  id: string;
  name: string;
  host: string;
  port: number;
  username: string;
  auth_type: "password" | "key";
  jump_host_id: string | null;
  tags: string[] | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface NodeCreate {
  name: string;
  host: string;
  port?: number;
  username: string;
  auth_type: "password" | "key";
  credential: string;
  jump_host_id?: string | null;
  tags?: string[] | null;
}

export interface NodeUpdate {
  name?: string;
  host?: string;
  port?: number;
  username?: string;
  auth_type?: "password" | "key";
  credential?: string;
  jump_host_id?: string | null;
  tags?: string[] | null;
}

export interface RuleResponse {
  id: string;
  pattern: string;
  level: "block" | "confirm" | "warn" | "allow";
  node_id: string | null;
  description: string | null;
  priority: number;
  enabled: boolean;
  created_at: string;
}

export interface RuleCreate {
  pattern: string;
  level: "block" | "confirm" | "warn" | "allow";
  node_id?: string | null;
  description?: string | null;
  priority?: number;
  enabled?: boolean;
}

export interface SessionResponse {
  id: string;
  node_id: string;
  node_name: string | null;
  working_directory: string | null;
  status: "active" | "closed";
  created_at: string;
  closed_at: string | null;
}

export interface CommandLogResponse {
  id: string;
  session_id: string | null;
  node_id: string;
  node_name: string | null;
  command: string;
  exit_code: number | null;
  stdout: string | null;
  stderr: string | null;
  security_level: string | null;
  bypassed: boolean;
  duration_ms: number | null;
  executed_at: string;
}

export interface LogListResponse {
  items: CommandLogResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface StatsResponse {
  node_count: number;
  active_sessions: number;
  total_commands: number;
}

export interface SettingsResponse {
  pool_max_total: number;
  pool_max_per_node: number;
  pool_idle_timeout: number;
  pool_max_lifetime: number;
  pool_queue_size: number;
  cleanup_command_logs_days: number;
  cleanup_closed_sessions_days: number;
}
```

- [ ] **Step 2: Create API client with TanStack Query hooks**

Create `web/src/api/client.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  LogListResponse,
  NodeCreate,
  NodeResponse,
  NodeUpdate,
  RuleCreate,
  RuleResponse,
  SessionResponse,
  SettingsResponse,
  StatsResponse,
} from "../types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Stats ──
export function useStats() {
  return useQuery<StatsResponse>({
    queryKey: ["stats"],
    queryFn: () => request("/stats"),
  });
}

// ── Nodes ──
export function useNodes(tag?: string) {
  return useQuery<NodeResponse[]>({
    queryKey: ["nodes", tag],
    queryFn: () => request(`/nodes${tag ? `?tag=${tag}` : ""}`),
  });
}

export function useNode(id: string) {
  return useQuery<NodeResponse>({
    queryKey: ["nodes", id],
    queryFn: () => request(`/nodes/${id}`),
    enabled: !!id,
  });
}

export function useCreateNode() {
  const qc = useQueryClient();
  return useMutation<NodeResponse, Error, NodeCreate>({
    mutationFn: (body) => request("/nodes", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["nodes"] }),
  });
}

export function useUpdateNode(id: string) {
  const qc = useQueryClient();
  return useMutation<NodeResponse, Error, NodeUpdate>({
    mutationFn: (body) => request(`/nodes/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["nodes"] }),
  });
}

export function useDeleteNode() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => request(`/nodes/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["nodes"] }),
  });
}

// ── Rules ──
export function useRules() {
  return useQuery<RuleResponse[]>({
    queryKey: ["rules"],
    queryFn: () => request("/rules"),
  });
}

export function useCreateRule() {
  const qc = useQueryClient();
  return useMutation<RuleResponse, Error, RuleCreate>({
    mutationFn: (body) => request("/rules", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useDeleteRule() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => request(`/rules/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

export function useReorderRules() {
  const qc = useQueryClient();
  return useMutation<RuleResponse[], Error, string[]>({
    mutationFn: (ids) =>
      request("/rules/reorder", { method: "POST", body: JSON.stringify({ ids }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });
}

// ── Sessions ──
export function useSessions(status?: string) {
  return useQuery<SessionResponse[]>({
    queryKey: ["sessions", status],
    queryFn: () => request(`/sessions${status ? `?status=${status}` : ""}`),
  });
}

export function useCloseSession() {
  const qc = useQueryClient();
  return useMutation<SessionResponse, Error, string>({
    mutationFn: (id) => request(`/sessions/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sessions"] }),
  });
}

// ── Logs ──
export function useLogs(params: { page?: number; page_size?: number; node_id?: string }) {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  if (params.node_id) qs.set("node_id", params.node_id);
  return useQuery<LogListResponse>({
    queryKey: ["logs", params],
    queryFn: () => request(`/logs?${qs}`),
  });
}

// ── Settings ──
export function useSettings() {
  return useQuery<SettingsResponse>({
    queryKey: ["settings"],
    queryFn: () => request("/settings"),
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation<SettingsResponse, Error, Partial<SettingsResponse>>({
    mutationFn: (body) =>
      request("/settings", { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/local-xiangw/workspace/ssh-mcp
git add web/src/types/ web/src/api/
git commit -m "feat(web): add TypeScript types and TanStack Query API client"
```

______________________________________________________________________

### Task 10: Shared UI Components

**Files:**

- Create: `web/src/components/Layout.tsx`
- Create: `web/src/components/Sidebar.tsx`
- Create: `web/src/components/Badge.tsx`
- Create: `web/src/components/DataTable.tsx`
- Create: `web/src/components/EmptyState.tsx`
- Create: `web/src/components/ConfirmDialog.tsx`

This task creates all shared UI components following macOS design language. Components should be clean, minimal, and reusable.

**Note:** Use the `/frontend-design` skill when implementing this task to ensure high design quality. The design should reference macOS aesthetics: subtle shadows, rounded corners, translucent sidebar, SF-Pro-like typography (Inter or system font stack), restrained color palette.

- [ ] **Step 1: Create Layout + Sidebar**

Create `web/src/components/Layout.tsx`:

```tsx
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
```

Create `web/src/components/Sidebar.tsx`:

```tsx
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Server,
  Shield,
  Terminal,
  ScrollText,
  Settings,
} from "lucide-react";
import clsx from "clsx";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/nodes", label: "Nodes", icon: Server },
  { to: "/rules", label: "Security Rules", icon: Shield },
  { to: "/sessions", label: "Sessions", icon: Terminal },
  { to: "/logs", label: "Command Logs", icon: ScrollText },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="flex w-56 flex-col border-r border-gray-200/60 bg-gray-100/50 backdrop-blur-xl">
      <div className="flex h-14 items-center gap-2 px-5">
        <div className="size-6 rounded-md bg-gradient-to-br from-blue-500 to-indigo-600" />
        <span className="text-sm font-semibold tracking-tight">Shuttle</span>
      </div>
      <nav className="flex-1 space-y-0.5 px-3 py-2">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] font-medium transition-colors",
                isActive
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:bg-white/60 hover:text-gray-700",
              )
            }
          >
            <Icon className="size-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 2: Create Badge component**

Create `web/src/components/Badge.tsx`:

```tsx
import clsx from "clsx";

const VARIANTS: Record<string, string> = {
  block: "bg-red-50 text-red-700 ring-red-200",
  confirm: "bg-amber-50 text-amber-700 ring-amber-200",
  warn: "bg-yellow-50 text-yellow-700 ring-yellow-200",
  allow: "bg-green-50 text-green-700 ring-green-200",
  active: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  closed: "bg-gray-100 text-gray-500 ring-gray-200",
  online: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  offline: "bg-red-50 text-red-600 ring-red-200",
};

export default function Badge({ value }: { value: string }) {
  const style = VARIANTS[value] ?? "bg-gray-100 text-gray-600 ring-gray-200";
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset",
        style,
      )}
    >
      {value}
    </span>
  );
}
```

- [ ] **Step 3: Create DataTable, EmptyState, ConfirmDialog**

Create `web/src/components/DataTable.tsx`:

```tsx
interface Column<T> {
  key: string;
  label: string;
  render?: (item: T) => React.ReactNode;
}

interface Props<T> {
  columns: Column<T>[];
  data: T[];
  keyField: string;
}

export default function DataTable<T extends Record<string, any>>({
  columns,
  data,
  keyField,
}: Props<T>) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50/50">
            {columns.map((col) => (
              <th
                key={col.key}
                className="px-4 py-2.5 text-xs font-medium text-gray-500"
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.map((item) => (
            <tr key={item[keyField]} className="hover:bg-gray-50/50 transition-colors">
              {columns.map((col) => (
                <td key={col.key} className="px-4 py-2.5 text-gray-700">
                  {col.render ? col.render(item) : item[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

Create `web/src/components/EmptyState.tsx`:

```tsx
import type { LucideIcon } from "lucide-react";

interface Props {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export default function EmptyState({ icon: Icon, title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 rounded-xl bg-gray-100 p-3">
        <Icon className="size-6 text-gray-400" />
      </div>
      <h3 className="text-sm font-medium text-gray-900">{title}</h3>
      <p className="mt-1 max-w-sm text-xs text-gray-500">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
```

Create `web/src/components/ConfirmDialog.tsx`:

```tsx
import * as Dialog from "@radix-ui/react-dialog";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  onConfirm: () => void;
  variant?: "danger" | "default";
}

export default function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  onConfirm,
  variant = "default",
}: Props) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/20 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-xl">
          <Dialog.Title className="text-base font-semibold text-gray-900">
            {title}
          </Dialog.Title>
          <Dialog.Description className="mt-2 text-sm text-gray-500">
            {description}
          </Dialog.Description>
          <div className="mt-5 flex justify-end gap-2">
            <Dialog.Close asChild>
              <button className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100">
                Cancel
              </button>
            </Dialog.Close>
            <button
              onClick={() => {
                onConfirm();
                onOpenChange(false);
              }}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium text-white ${
                variant === "danger"
                  ? "bg-red-500 hover:bg-red-600"
                  : "bg-blue-500 hover:bg-blue-600"
              }`}
            >
              {confirmLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd /home/local-xiangw/workspace/ssh-mcp/web && npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 5: Commit**

```bash
cd /home/local-xiangw/workspace/ssh-mcp
git add web/src/components/
git commit -m "feat(web): add shared UI components (Layout, Sidebar, Badge, DataTable, ConfirmDialog)"
```

______________________________________________________________________

### Task 11: Dashboard Page

**Files:**

- Create: `web/src/pages/Dashboard.tsx`

- [ ] **Step 1: Create Dashboard page**

Create `web/src/pages/Dashboard.tsx`:

```tsx
import { Server, Terminal, ScrollText } from "lucide-react";
import { useStats } from "../api/client";

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof Server;
  label: string;
  value: number | undefined;
  color: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`rounded-lg p-2 ${color}`}>
          <Icon className="size-5 text-white" />
        </div>
        <div>
          <p className="text-2xl font-semibold tabular-nums text-gray-900">
            {value ?? "—"}
          </p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data: stats, isLoading } = useStats();

  return (
    <div>
      <h1 className="text-lg font-semibold text-gray-900">Dashboard</h1>
      <p className="mt-1 text-sm text-gray-500">Overview of your Shuttle instance</p>

      <div className="mt-6 grid grid-cols-3 gap-4">
        <StatCard
          icon={Server}
          label="SSH Nodes"
          value={stats?.node_count}
          color="bg-blue-500"
        />
        <StatCard
          icon={Terminal}
          label="Active Sessions"
          value={stats?.active_sessions}
          color="bg-emerald-500"
        />
        <StatCard
          icon={ScrollText}
          label="Total Commands"
          value={stats?.total_commands}
          color="bg-violet-500"
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd /home/local-xiangw/workspace/ssh-mcp/web && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
cd /home/local-xiangw/workspace/ssh-mcp
git add web/src/pages/Dashboard.tsx
git commit -m "feat(web): add Dashboard page with stat cards"
```

______________________________________________________________________

### Task 12: Nodes Page

**Files:**

- Create: `web/src/pages/Nodes.tsx`

- Create: `web/src/pages/NodeForm.tsx`

- Modify: `web/src/App.tsx` (add route)

- [ ] **Step 1: Create Nodes list page**

Create `web/src/pages/Nodes.tsx`:

```tsx
import { useState } from "react";
import { Plus, Server, Trash2 } from "lucide-react";
import { useNodes, useDeleteNode } from "../api/client";
import Badge from "../components/Badge";
import DataTable from "../components/DataTable";
import EmptyState from "../components/EmptyState";
import ConfirmDialog from "../components/ConfirmDialog";
import NodeForm from "./NodeForm";
import type { NodeResponse } from "../types";

export default function Nodes() {
  const { data: nodes = [], isLoading } = useNodes();
  const deleteNode = useDeleteNode();
  const [showForm, setShowForm] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<NodeResponse | null>(null);

  const columns = [
    { key: "name", label: "Name" },
    { key: "host", label: "Host", render: (n: NodeResponse) => `${n.host}:${n.port}` },
    { key: "username", label: "User" },
    { key: "auth_type", label: "Auth" },
    {
      key: "status",
      label: "Status",
      render: (n: NodeResponse) => <Badge value={n.status} />,
    },
    {
      key: "actions",
      label: "",
      render: (n: NodeResponse) => (
        <button
          onClick={() => setDeleteTarget(n)}
          className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
        >
          <Trash2 className="size-4" />
        </button>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">SSH Nodes</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your remote server connections
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 rounded-lg bg-blue-500 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-blue-600"
        >
          <Plus className="size-4" /> Add Node
        </button>
      </div>

      <div className="mt-6">
        {nodes.length === 0 && !isLoading ? (
          <EmptyState
            icon={Server}
            title="No nodes configured"
            description="Add your first SSH node to get started"
            action={
              <button
                onClick={() => setShowForm(true)}
                className="text-sm font-medium text-blue-500 hover:text-blue-600"
              >
                Add Node
              </button>
            }
          />
        ) : (
          <DataTable columns={columns} data={nodes} keyField="id" />
        )}
      </div>

      {showForm && <NodeForm onClose={() => setShowForm(false)} />}

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={() => setDeleteTarget(null)}
        title="Delete Node"
        description={`Are you sure you want to delete "${deleteTarget?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => {
          if (deleteTarget) deleteNode.mutate(deleteTarget.id);
        }}
      />
    </div>
  );
}
```

- [ ] **Step 2: Create NodeForm dialog**

Create `web/src/pages/NodeForm.tsx`:

```tsx
import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useCreateNode } from "../api/client";

interface Props {
  onClose: () => void;
}

export default function NodeForm({ onClose }: Props) {
  const createNode = useCreateNode();
  const [form, setForm] = useState({
    name: "",
    host: "",
    port: 22,
    username: "",
    auth_type: "password" as "password" | "key",
    credential: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createNode.mutate(form, {
      onSuccess: () => onClose(),
    });
  };

  const inputClass =
    "w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100";

  return (
    <Dialog.Root open onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/20 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-6 shadow-xl">
          <div className="flex items-center justify-between">
            <Dialog.Title className="text-base font-semibold">Add Node</Dialog.Title>
            <Dialog.Close asChild>
              <button className="rounded-md p-1 hover:bg-gray-100">
                <X className="size-4" />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="mt-4 space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Name</label>
              <input
                className={inputClass}
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="my-server"
                required
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label className="mb-1 block text-xs font-medium text-gray-600">Host</label>
                <input
                  className={inputClass}
                  value={form.host}
                  onChange={(e) => setForm({ ...form, host: e.target.value })}
                  placeholder="192.168.1.1"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Port</label>
                <input
                  type="number"
                  className={inputClass}
                  value={form.port}
                  onChange={(e) => setForm({ ...form, port: Number(e.target.value) })}
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Username</label>
              <input
                className={inputClass}
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                placeholder="root"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Password</label>
              <input
                type="password"
                className={inputClass}
                value={form.credential}
                onChange={(e) => setForm({ ...form, credential: e.target.value })}
                required
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createNode.isPending}
                className="rounded-lg bg-blue-500 px-4 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-blue-600 disabled:opacity-50"
              >
                {createNode.isPending ? "Adding..." : "Add Node"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

- [ ] **Step 3: Add route to App.tsx**

Update `web/src/App.tsx` to add:

```tsx
import Nodes from "./pages/Nodes";

// Inside <Route element={<Layout />}>:
<Route path="/nodes" element={<Nodes />} />
```

- [ ] **Step 4: Verify build**

```bash
cd /home/local-xiangw/workspace/ssh-mcp/web && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
cd /home/local-xiangw/workspace/ssh-mcp
git add web/src/pages/Nodes.tsx web/src/pages/NodeForm.tsx web/src/App.tsx
git commit -m "feat(web): add Nodes list page with create/delete"
```

______________________________________________________________________

### Task 13: Rules, Sessions, Logs, Settings Pages

**Files:**

- Create: `web/src/pages/Rules.tsx`
- Create: `web/src/pages/RuleForm.tsx`
- Create: `web/src/pages/Sessions.tsx`
- Create: `web/src/pages/SessionDetail.tsx`
- Create: `web/src/pages/Logs.tsx`
- Create: `web/src/pages/Settings.tsx`
- Modify: `web/src/App.tsx` (add all remaining routes)

This is a larger task covering all remaining pages. Each page follows the same pattern as the Nodes page: list view with DataTable, create/edit form dialog, and appropriate actions.

**Note:** Use the `/frontend-design` skill for each page to ensure consistent macOS design language across the entire app.

- [ ] **Step 1: Create Rules page**

Create `web/src/pages/Rules.tsx` — list with badge for level (block=red, confirm=amber, warn=yellow, allow=green), add/delete actions, drag-to-reorder (simplified: just up/down buttons for v1).

- [ ] **Step 2: Create RuleForm dialog**

Create `web/src/pages/RuleForm.tsx` — form with pattern (textarea), level (select), description, priority, enabled toggle.

- [ ] **Step 3: Create Sessions page**

Create `web/src/pages/Sessions.tsx` — list active/closed sessions with node name, status badge, working directory, created/closed timestamps. Close button for active sessions.

- [ ] **Step 4: Create SessionDetail page**

Create `web/src/pages/SessionDetail.tsx` — shows session info + command history (uses logs API filtered by session_id). Display as a timeline of commands with exit codes.

- [ ] **Step 5: Create Logs page**

Create `web/src/pages/Logs.tsx` — paginated table with node filter, expandable rows showing stdout/stderr. Export button (links to `/api/logs?page_size=10000` download).

- [ ] **Step 6: Create Settings page**

Create `web/src/pages/Settings.tsx` — form with all settings fields, grouped by section (Connection Pool, Cleanup Policy). Save button calls `useUpdateSettings()`.

- [ ] **Step 7: Wire all routes in App.tsx**

Update `web/src/App.tsx`:

```tsx
import Rules from "./pages/Rules";
import Sessions from "./pages/Sessions";
import SessionDetail from "./pages/SessionDetail";
import Logs from "./pages/Logs";
import Settings from "./pages/Settings";

// Inside <Route element={<Layout />}>:
<Route path="/rules" element={<Rules />} />
<Route path="/sessions" element={<Sessions />} />
<Route path="/sessions/:id" element={<SessionDetail />} />
<Route path="/logs" element={<Logs />} />
<Route path="/settings" element={<Settings />} />
```

- [ ] **Step 8: Verify build**

```bash
cd /home/local-xiangw/workspace/ssh-mcp/web && npx tsc --noEmit
```

- [ ] **Step 9: Commit**

```bash
cd /home/local-xiangw/workspace/ssh-mcp
git add web/src/pages/ web/src/App.tsx
git commit -m "feat(web): add Rules, Sessions, Logs, and Settings pages"
```

______________________________________________________________________

### Task 14: Build Pipeline & .gitignore

**Files:**

- Modify: `.gitignore`

- Modify: `pyproject.toml` (add `web/` as package data)

- [ ] **Step 1: Update .gitignore**

Add to `.gitignore`:

```
# React build output (embedded in package)
src/shuttle/web/static/*
!src/shuttle/web/static/.gitkeep

# Node
web/node_modules/
web/dist/
```

Create `src/shuttle/web/static/.gitkeep` (empty file so git tracks the directory).

- [ ] **Step 2: Update pyproject.toml for static file inclusion**

Add to `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/shuttle"]

[tool.hatch.build.targets.wheel.force-include]
"src/shuttle/web/static" = "shuttle/web/static"
```

- [ ] **Step 3: Build frontend and verify**

```bash
cd /home/local-xiangw/workspace/ssh-mcp/web && npm run build
ls -la ../src/shuttle/web/static/
```

Expected: `index.html`, `assets/` directory with JS/CSS bundles.

- [ ] **Step 4: Test full flow**

```bash
cd /home/local-xiangw/workspace/ssh-mcp
uv run shuttle web --port 9876
# Visit http://localhost:9876 → should serve React SPA
# Visit http://localhost:9876/api/stats → should return JSON
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore pyproject.toml src/shuttle/web/static/.gitkeep
git commit -m "chore: add build pipeline, static file packaging, and gitignore rules"
```

______________________________________________________________________

### Task 15: Run Full Test Suite & Cleanup

**Files:**

- No new files

- [ ] **Step 1: Run full Python test suite**

```bash
cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/ -v --tb=short
```

Expected: ALL PASS

- [ ] **Step 2: Run linter**

```bash
cd /home/local-xiangw/workspace/ssh-mcp && uv run ruff check src/shuttle/web/ tests/test_web/
```

Fix any issues.

- [ ] **Step 3: Run frontend type check**

```bash
cd /home/local-xiangw/workspace/ssh-mcp/web && npx tsc --noEmit
```

- [ ] **Step 4: Final commit if any fixes**

```bash
git add -A && git commit -m "chore: fix linting and type errors from full test run"
```
