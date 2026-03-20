# Shuttle v2 Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Shuttle from v1 to v2 — add service mode (FastMCP + FastAPI on single ASGI app), per-node security rule inheritance, MCP node management tools, and a per-node Activity view in the frontend.

**Architecture:** Incremental upgrade of v1. Core engine (connection pool, session, proxy, credentials) stays unchanged. Key changes: CommandGuard becomes async with DB-per-call evaluation, FastMCP mounts inside FastAPI for service mode, React frontend gets a unified Activity page replacing separate Dashboard/Sessions/Logs.

**Tech Stack:** Python 3.12+, FastMCP 2.x (`http_app()`), FastAPI, AsyncSSH, SQLAlchemy 2.0 async, React 18, TypeScript, Vite, Tailwind CSS 4

**Spec:** `docs/superpowers/specs/2026-03-20-shuttle-v2-design.md`

---

## File Structure (changes only)

```
src/shuttle/
├── cli.py                        # MODIFY: remove web cmd, add serve cmd
├── core/
│   └── security.py               # MODIFY: evaluate() → async, DB query per call
├── db/
│   ├── models.py                 # MODIFY: add source_rule_id, fix tags type
│   ├── repository.py             # MODIFY: add list_effective(), source_rule_id param, fix tag filter
│   └── engine.py                 # MODIFY: add schema migration in init_db()
├── mcp/
│   ├── server.py                 # MODIFY: add create_service_app() for ASGI mode
│   └── tools.py                  # MODIFY: fix node_id bug, add ssh_add_node/ssh_remove_node
├── web/
│   ├── app.py                    # MODIFY: accept injected core objects, mount FastMCP
│   ├── deps.py                   # MODIFY: support injected engine/factory (not just globals)
│   ├── schemas.py                # MODIFY: add source_rule_id to Rule schemas
│   └── routes/
│       └── rules.py              # MODIFY: add GET /api/rules/effective/:node_id
web/src/
├── App.tsx                       # MODIFY: replace routes
├── api/client.ts                 # MODIFY: add useEffectiveRules hook
├── components/
│   └── Sidebar.tsx               # MODIFY: node-first navigation
├── pages/
│   ├── Activity.tsx              # CREATE: per-node command log browser
│   ├── Dashboard.tsx             # DELETE (merged into Activity)
│   ├── Sessions.tsx              # DELETE (merged into Activity)
│   ├── SessionDetail.tsx         # DELETE (merged into Activity)
│   └── Logs.tsx                  # DELETE (merged into Activity)
tests/
├── test_core/test_security.py    # MODIFY: update for async evaluate
├── test_mcp/test_tools.py        # MODIFY: update for new tools + node_id fix
└── test_web/test_rules_api.py    # MODIFY: add effective rules test
```

---

### Task 1: Fix Node.tags Type (dict → list)

**Files:**
- Modify: `src/shuttle/db/models.py:39`
- Modify: `src/shuttle/db/repository.py:60-74`
- Modify: `tests/test_db/test_repository.py`

- [ ] **Step 1: Update model type annotation**

In `src/shuttle/db/models.py`, line 39, change:
```python
tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```
to:
```python
tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
```

- [ ] **Step 2: Fix tag filtering in NodeRepo.list_all()**

In `src/shuttle/db/repository.py`, replace the tag filtering logic (lines 66-72):
```python
        if tag:
            nodes = [
                n
                for n in nodes
                if n.tags and tag in (n.tags.values() if isinstance(n.tags, dict) else n.tags)
            ]
```
with:
```python
        if tag:
            nodes = [n for n in nodes if n.tags and tag in n.tags]
```

- [ ] **Step 3: Update NodeRepo.create() parameter type hint**

In `src/shuttle/db/repository.py`, line 25, change `tags: dict | None = None` to `tags: list | None = None`.

- [ ] **Step 4: Run existing tests**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_db/ tests/test_web/test_nodes_api.py -v`
Expected: ALL PASS (tags were already stored as lists by the web API)

- [ ] **Step 5: Commit**

```bash
git add src/shuttle/db/models.py src/shuttle/db/repository.py
git commit -m "fix: change Node.tags from dict to list type, simplify tag filtering"
```

---

### Task 2: Add source_rule_id to SecurityRule + Schema Migration

**Files:**
- Modify: `src/shuttle/db/models.py:71-94`
- Modify: `src/shuttle/db/repository.py:102-122`
- Modify: `src/shuttle/db/engine.py:57-64`
- Modify: `src/shuttle/web/schemas.py`
- Test: `tests/test_db/test_models.py`

- [ ] **Step 1: Add source_rule_id field to SecurityRule model**

In `src/shuttle/db/models.py`, after line 86 (`enabled`), add:
```python
    source_rule_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, default=None
    )
```

- [ ] **Step 2: Add source_rule_id to RuleRepo.create()**

In `src/shuttle/db/repository.py`, add `source_rule_id: str | None = None` parameter to `RuleRepo.create()` (after `enabled` param), and pass it to the `SecurityRule()` constructor.

- [ ] **Step 3: Add schema migration to init_db()**

In `src/shuttle/db/engine.py`, after `Base.metadata.create_all`, add a migration check:

```python
async def init_db(engine: AsyncEngine) -> None:
    """Create tables and run lightweight migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Migration: add source_rule_id if missing (v1 → v2)
        if "sqlite" in str(engine.url):
            result = await conn.execute(text("PRAGMA table_info(security_rules)"))
            columns = [row[1] for row in result]
            if "source_rule_id" not in columns:
                await conn.execute(
                    text("ALTER TABLE security_rules ADD COLUMN source_rule_id VARCHAR(36)")
                )
        else:
            # PostgreSQL/MySQL: check information_schema
            result = await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'security_rules' AND column_name = 'source_rule_id'"
                )
            )
            if not result.fetchone():
                await conn.execute(
                    text("ALTER TABLE security_rules ADD COLUMN source_rule_id VARCHAR(36)")
                )
```

- [ ] **Step 4: Update Pydantic schemas**

In `src/shuttle/web/schemas.py`:
- Add `source_rule_id: str | None = None` to `RuleCreate`
- Add `source_rule_id: str | None = None` to `RuleResponse`

- [ ] **Step 5: Run tests**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/ -v --tb=short`
Expected: ALL PASS (new nullable field with default None is backward compatible)

- [ ] **Step 6: Commit**

```bash
git add src/shuttle/db/models.py src/shuttle/db/repository.py src/shuttle/db/engine.py src/shuttle/web/schemas.py
git commit -m "feat: add source_rule_id to SecurityRule for per-node rule inheritance"
```

---

### Task 3: Add RuleRepo.list_effective() + API Endpoint

**Depends on:** Task 2 (source_rule_id field must exist in RuleRepo.create())

**Files:**
- Modify: `src/shuttle/db/repository.py`
- Modify: `src/shuttle/web/routes/rules.py`
- Create: `tests/test_web/test_rules_effective.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_web/test_rules_effective.py`:

```python
"""Test effective rules endpoint (global + per-node merged)."""

import pytest
from shuttle.db.repository import NodeRepo, RuleRepo


@pytest.mark.asyncio
async def test_effective_rules_inherits_global(client, db_session):
    """Node with no overrides inherits all global rules."""
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(name="eff-node", host="10.0.0.1", username="u",
                                   auth_type="password", encrypted_credential="x")
    rule_repo = RuleRepo(db_session)
    await rule_repo.create(pattern="sudo .*", level="confirm", priority=10)
    await db_session.commit()

    resp = await client.get(f"/api/rules/effective/{node.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(r["pattern"] == "sudo .*" for r in data)


@pytest.mark.asyncio
async def test_effective_rules_node_override(client, db_session):
    """Node-specific rule overrides global rule with same pattern."""
    node_repo = NodeRepo(db_session)
    node = await node_repo.create(name="ovr-node", host="10.0.0.2", username="u",
                                   auth_type="password", encrypted_credential="x")
    rule_repo = RuleRepo(db_session)
    global_rule = await rule_repo.create(pattern="sudo .*", level="confirm", priority=10)
    await rule_repo.create(pattern="sudo .*", level="allow", priority=10,
                           node_id=node.id, source_rule_id=global_rule.id)
    await db_session.commit()

    resp = await client.get(f"/api/rules/effective/{node.id}")
    data = resp.json()
    sudo_rules = [r for r in data if r["pattern"] == "sudo .*"]
    assert len(sudo_rules) == 1
    assert sudo_rules[0]["level"] == "allow"


@pytest.mark.asyncio
async def test_effective_rules_node_not_found(client):
    resp = await client.get("/api/rules/effective/nonexistent")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_web/test_rules_effective.py -v`
Expected: FAIL (endpoint doesn't exist)

- [ ] **Step 3: Implement RuleRepo.list_effective()**

Add to `src/shuttle/db/repository.py` in `RuleRepo` class:

```python
    async def list_effective(self, node_id: str) -> list["SecurityRule"]:
        """Return merged global + node-specific rules.

        Node-specific rules override global rules with the same pattern.
        """
        # Fetch global rules (node_id IS NULL)
        global_q = (
            select(SecurityRule)
            .where(SecurityRule.node_id.is_(None))
            .order_by(SecurityRule.priority)
        )
        global_result = await self._session.execute(global_q)
        global_rules = list(global_result.scalars().all())

        # Fetch node-specific rules
        node_q = (
            select(SecurityRule)
            .where(SecurityRule.node_id == node_id)
            .order_by(SecurityRule.priority)
        )
        node_result = await self._session.execute(node_q)
        node_rules = list(node_result.scalars().all())

        # Merge: node rules override globals with same pattern
        node_patterns = {r.pattern for r in node_rules}
        merged = [r for r in global_rules if r.pattern not in node_patterns]
        merged.extend(node_rules)
        merged.sort(key=lambda r: r.priority)
        return merged
```

- [ ] **Step 4: Add API endpoint**

In `src/shuttle/web/routes/rules.py`, add:

```python
@router.get("/effective/{node_id}", response_model=list[RuleResponse])
async def get_effective_rules(
    node_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Return effective rules for a node (global defaults + node overrides merged)."""
    from shuttle.db.repository import NodeRepo

    node_repo = NodeRepo(db)
    node = await node_repo.get_by_id(node_id)
    if not node:
        raise HTTPException(404, "Node not found")

    repo = RuleRepo(db)
    return await repo.list_effective(node_id)
```

**Important:** Place this route BEFORE the `/{rule_id}` routes to avoid path conflicts.

- [ ] **Step 5: Register route in app.py if needed**

The rules router is already included. No changes to app.py needed.

- [ ] **Step 6: Run tests**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_web/test_rules_effective.py tests/test_web/test_rules_api.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add src/shuttle/db/repository.py src/shuttle/web/routes/rules.py tests/test_web/test_rules_effective.py
git commit -m "feat: add effective rules endpoint with per-node inheritance"
```

---

### Task 4: Refactor CommandGuard.evaluate() to Async DB Query

**Files:**
- Modify: `src/shuttle/core/security.py:100-195`
- Modify: `src/shuttle/mcp/tools.py:111`
- Modify: `src/shuttle/mcp/server.py:88-102`
- Modify: `tests/test_core/test_security.py`

This is the biggest refactor. `CommandGuard` currently loads rules into memory at startup and evaluates synchronously. We change it to query the DB per call, making it async and ensuring rule changes from Web UI take effect immediately.

- [ ] **Step 1: Refactor CommandGuard**

In `src/shuttle/core/security.py`, replace the `CommandGuard` class (lines 100-195):

```python
class CommandGuard:
    """Evaluates commands against security rules from the database.

    Rules are queried per call — no in-memory cache — so changes via
    Web UI or MCP take effect immediately.
    """

    async def evaluate(
        self,
        command: str,
        node_id: str,
        db_session: "AsyncSession",
        bypass_patterns: list[str] | None = None,
    ) -> SecurityDecision:
        """Evaluate a command against global + node-specific rules."""
        from shuttle.db.models import SecurityRule

        # Query global rules (node_id IS NULL) + node-specific rules
        query = (
            select(SecurityRule)
            .where(
                SecurityRule.enabled.is_(True),
                (SecurityRule.node_id.is_(None)) | (SecurityRule.node_id == node_id),
            )
            .order_by(SecurityRule.priority, SecurityRule.node_id.nullsfirst())
        )
        result = await db_session.execute(query)
        rules = result.scalars().all()

        # Merge: node-specific rules override globals with same pattern
        seen_patterns: dict[str, SecurityRule] = {}
        for rule in rules:
            if rule.pattern in seen_patterns:
                # Node-specific overrides global
                if rule.node_id is not None:
                    seen_patterns[rule.pattern] = rule
            else:
                seen_patterns[rule.pattern] = rule

        bypassed = set(bypass_patterns or [])

        for rule in sorted(seen_patterns.values(), key=lambda r: r.priority):
            try:
                if re.search(rule.pattern, command):
                    level = SecurityLevel(rule.level)

                    if level == SecurityLevel.BLOCK:
                        return SecurityDecision(
                            level=level,
                            matched_rule=rule.id,
                            message=f"BLOCKED: {rule.description or rule.pattern}",
                        )

                    if rule.pattern in bypassed:
                        continue

                    return SecurityDecision(
                        level=level,
                        matched_rule=rule.id,
                        message=rule.description or "",
                    )
            except re.error:
                continue

        return SecurityDecision(level=SecurityLevel.ALLOW)
```

Remove `load_rules()`, `_CompiledRule`, and the `_rules` attribute entirely.

Add the import at the top of the file:
```python
from sqlalchemy import select
```

- [ ] **Step 2: Update tools.py to pass db_session to evaluate()**

In `src/shuttle/mcp/tools.py`, the `_execute_command_logic` function calls `guard.evaluate()` at line 111. Change:

```python
decision = guard.evaluate(command, resolved_node, bypass_patterns)
```
to:
```python
async with db_session_ctx() as db_sess:
    decision = await guard.evaluate(command, resolved_node, db_sess, bypass_patterns)
```

Also update the bypass pattern lookup (lines 134-141) — `guard._rules` no longer exists. The matched rule ID is now in `decision.matched_rule` (which is the rule's DB ID). To get the pattern string for session bypass, query the rule:

```python
if bypass_scope == "session" and session_obj and decision.matched_rule:
    async with db_session_ctx() as db_sess:
        from shuttle.db.repository import RuleRepo
        rule_repo = RuleRepo(db_sess)
        rule = await rule_repo.get_by_id(decision.matched_rule)
        if rule:
            session_obj.bypass_patterns.add(rule.pattern)
```

- [ ] **Step 3: Remove load_rules() from server.py**

In `src/shuttle/mcp/server.py`, remove lines 88-102 (the block that loads rules into CommandGuard). The guard no longer needs preloading. Just create an empty `CommandGuard()`:

```python
guard = CommandGuard()
```

- [ ] **Step 4: Update security tests**

In `tests/test_core/test_security.py`, update all `evaluate()` calls to be async and pass a DB session. The test will need to:
1. Create an in-memory SQLite DB
2. Seed rules into the DB
3. Pass the session to `evaluate()`

Replace the `_guard()` helper and tests:

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from shuttle.db.models import Base, SecurityRule
from shuttle.core.security import CommandGuard, SecurityLevel


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _seed_rules(db: AsyncSession, rules: list[dict]):
    for r in rules:
        db.add(SecurityRule(**r))
    await db.commit()


SAMPLE_RULES = [
    {"pattern": r"^rm -rf /$", "level": "block", "priority": 1, "description": "nuke root"},
    {"pattern": r"sudo .*", "level": "confirm", "priority": 10, "description": "sudo"},
    {"pattern": r"pip install", "level": "warn", "priority": 20, "description": "pip"},
    {"pattern": r".*", "level": "allow", "priority": 100, "description": "fallback"},
]


@pytest.mark.asyncio
async def test_evaluate_block(db_session):
    await _seed_rules(db_session, SAMPLE_RULES)
    guard = CommandGuard()
    decision = await guard.evaluate("rm -rf /", "node1", db_session)
    assert decision.level == SecurityLevel.BLOCK


@pytest.mark.asyncio
async def test_evaluate_confirm(db_session):
    await _seed_rules(db_session, SAMPLE_RULES)
    guard = CommandGuard()
    decision = await guard.evaluate("sudo apt update", "node1", db_session)
    assert decision.level == SecurityLevel.CONFIRM


@pytest.mark.asyncio
async def test_evaluate_warn(db_session):
    await _seed_rules(db_session, SAMPLE_RULES)
    guard = CommandGuard()
    decision = await guard.evaluate("pip install requests", "node1", db_session)
    assert decision.level == SecurityLevel.WARN


@pytest.mark.asyncio
async def test_evaluate_allow(db_session):
    await _seed_rules(db_session, SAMPLE_RULES)
    guard = CommandGuard()
    decision = await guard.evaluate("ls -la", "node1", db_session)
    assert decision.level == SecurityLevel.ALLOW
```

- [ ] **Step 5: Run all tests**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_core/test_security.py tests/test_mcp/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/shuttle/core/security.py src/shuttle/mcp/tools.py src/shuttle/mcp/server.py tests/test_core/test_security.py
git commit -m "refactor: CommandGuard.evaluate() async with per-call DB query for live rule updates"
```

---

### Task 5: Fix CommandLog node_id Bug (name → UUID)

**Files:**
- Modify: `src/shuttle/mcp/tools.py:87-108, 175-187`

- [ ] **Step 1: Resolve node to (name, uuid) tuple**

In `src/shuttle/mcp/tools.py`, in `_execute_command_logic()`, after node resolution (around line 108), add UUID tracking. Change the resolution block to store both name and ID:

```python
resolved_node: str | None = None  # node name (for pool/guard)
resolved_node_id: str | None = None  # node UUID (for DB logging)
```

After resolving via session:
```python
resolved_node = session_obj.node_id  # This is actually the node name
# Look up UUID
async with db_session_ctx() as db_sess:
    repo = node_repo_factory(db_sess)
    node_obj = await repo.get_by_name(resolved_node)
    resolved_node_id = node_obj.id if node_obj else None
```

After resolving via explicit node name or auto-select:
```python
resolved_node = all_nodes[0].name
resolved_node_id = all_nodes[0].id
```

- [ ] **Step 2: Use UUID for DB logging**

In the logging block (around line 178), change `node_id=resolved_node` to `node_id=resolved_node_id`:

```python
await log_repo.create(
    node_id=resolved_node_id or "",
    command=command,
    ...
)
```

- [ ] **Step 3: Run tests**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_mcp/ -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/shuttle/mcp/tools.py
git commit -m "fix: store node UUID (not name) in CommandLog.node_id for correct FK"
```

---

### Task 6: Add ssh_add_node and ssh_remove_node MCP Tools

**Files:**
- Modify: `src/shuttle/mcp/tools.py`
- Modify: `src/shuttle/mcp/server.py` (pass credential_manager to register_tools)

- [ ] **Step 1: Add tools to register_tools()**

In `src/shuttle/mcp/tools.py`, update `register_tools` signature to accept `cred_mgr`:

```python
def register_tools(
    mcp, pool, guard, token_store, session_mgr, db_session_ctx, node_repo_factory,
    cred_mgr=None,  # NEW: CredentialManager for ssh_add_node
):
```

Add the two new tools inside `register_tools()`:

```python
    @mcp.tool()
    async def ssh_add_node(
        name: str,
        host: str,
        port: int = 22,
        username: str = "",
        password: str | None = None,
        private_key: str | None = None,
        jump_host: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Add a new SSH node to Shuttle."""
        if not password and not private_key:
            return "Error: provide either password or private_key"

        auth_type = "key" if private_key else "password"
        credential = private_key or password or ""

        if not cred_mgr:
            return "Error: credential manager not available"
        encrypted = cred_mgr.encrypt(credential)

        # Resolve jump_host name to ID
        jump_host_id = None
        if jump_host:
            async with db_session_ctx() as db_sess:
                repo = node_repo_factory(db_sess)
                jh = await repo.get_by_name(jump_host)
                if not jh:
                    return f"Error: jump host '{jump_host}' not found"
                jump_host_id = jh.id

        async with db_session_ctx() as db_sess:
            repo = node_repo_factory(db_sess)
            existing = await repo.get_by_name(name)
            if existing:
                return f"Error: node '{name}' already exists"
            node = await repo.create(
                name=name, host=host, port=port, username=username,
                auth_type=auth_type, encrypted_credential=encrypted,
                jump_host_id=jump_host_id, tags=tags,
            )

        # Register in connection pool
        from shuttle.core.proxy import NodeConnectInfo
        info = NodeConnectInfo(
            node_id=name, hostname=host, port=port, username=username,
            password=password if auth_type == "password" else None,
            private_key=private_key if auth_type == "key" else None,
        )
        pool.register_node(info)

        return f"Node '{name}' added successfully (id={node.id})"

    @mcp.tool()
    async def ssh_remove_node(name: str) -> str:
        """Remove an SSH node from Shuttle."""
        async with db_session_ctx() as db_sess:
            repo = node_repo_factory(db_sess)
            node = await repo.get_by_name(name)
            if not node:
                return f"Error: node '{name}' not found"
            await repo.delete(node.id)

        # Close idle connections for this node
        try:
            await pool.close_node(name)
        except (KeyError, Exception):
            pass  # Not in pool (never connected)

        return f"Node '{name}' removed successfully"
```

- [ ] **Step 2: Pass cred_mgr from server.py**

In `src/shuttle/mcp/server.py`, the `create_mcp_server` function already creates a `CredentialManager`. Pass it to `register_tools`:

```python
register_tools(
    mcp, pool, guard, token_store, session_mgr,
    db_session_ctx, NodeRepo,
    cred_mgr=cred_mgr,  # NEW
)
```

- [ ] **Step 3: Run tests**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_mcp/ -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/shuttle/mcp/tools.py src/shuttle/mcp/server.py
git commit -m "feat: add ssh_add_node and ssh_remove_node MCP tools"
```

---

### Task 7: Refactor web/deps.py for Dependency Injection

**Files:**
- Modify: `src/shuttle/web/deps.py`
- Modify: `src/shuttle/web/app.py`
- Modify: `tests/test_web/conftest.py`

In service mode, the engine and session factory are created by the service orchestrator (not by `init_db_deps`). We need deps.py to accept injected instances.

- [ ] **Step 1: Update deps.py to support injection**

Replace `src/shuttle/web/deps.py`:

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


def init_db_deps(
    db_url: str | None = None,
    api_token: str | None = None,
    engine=None,
    session_factory=None,
) -> None:
    """Initialize deps. Accepts pre-built engine/factory (service mode) or creates from URL."""
    global _engine, _session_factory, _api_token
    _api_token = api_token
    if engine and session_factory:
        _engine = engine
        _session_factory = session_factory
    else:
        _engine = create_db_engine(db_url)
        _session_factory = create_session_factory(_engine)


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    if _api_token is None:
        return
    if credentials is None or credentials.credentials != _api_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing token")


async def get_db_session() -> AsyncIterator[AsyncSession]:
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

- [ ] **Step 2: Update app.py to pass through injection params**

In `src/shuttle/web/app.py`, update `create_app` signature:

```python
def create_app(
    db_url: str | None = None,
    api_token: str | None = None,
    engine=None,
    session_factory=None,
) -> FastAPI:
    init_db_deps(db_url, api_token=api_token, engine=engine, session_factory=session_factory)
    ...
```

- [ ] **Step 3: Run tests**

Run: `cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/test_web/ -v`
Expected: ALL PASS (tests don't pass engine/factory, so it falls back to creating from URL)

- [ ] **Step 4: Commit**

```bash
git add src/shuttle/web/deps.py src/shuttle/web/app.py
git commit -m "refactor: deps.py supports injected engine/session_factory for service mode"
```

---

### Task 8: Add `shuttle serve` Command (Service Mode)

**Files:**
- Modify: `src/shuttle/mcp/server.py`
- Modify: `src/shuttle/cli.py`

This is the key new feature: running FastMCP + FastAPI on a single ASGI app.

- [ ] **Step 1: Add create_service_app() to server.py**

Add a new function to `src/shuttle/mcp/server.py`:

```python
async def create_service_app(
    host: str = "127.0.0.1",
    port: int = 9876,
    api_token: str | None = None,
    shuttle_dir: Path | None = None,
    db_url: str | None = None,
) -> "FastAPI":
    """Create a unified ASGI app: FastMCP (at /mcp) + FastAPI (at /api + /).

    Both share the same engine, pool, guard, and session manager.
    """
    from contextlib import asynccontextmanager

    from fastapi import Depends, FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles

    from shuttle.core.config import ShuttleConfig
    from shuttle.core.connection_pool import ConnectionPool, PoolConfig
    from shuttle.core.credentials import CredentialManager
    from shuttle.core.proxy import NodeConnectInfo
    from shuttle.core.security import CommandGuard, ConfirmTokenStore
    from shuttle.core.session import SessionManager
    from shuttle.db.engine import create_db_engine, create_session_factory, init_db
    from shuttle.db.repository import NodeRepo, RuleRepo
    from shuttle.db.seeds import seed_default_rules
    from shuttle.web.deps import init_db_deps, verify_token

    # --- Config ---
    config = ShuttleConfig()
    if shuttle_dir:
        config.shuttle_dir = shuttle_dir
    config.shuttle_dir.mkdir(parents=True, exist_ok=True)

    resolved_url = db_url or config.db_url
    if "sqlite" in resolved_url and "~" in resolved_url:
        resolved_url = resolved_url.replace("~", str(Path.home()))

    # --- Shared core objects ---
    engine = create_db_engine(resolved_url)
    session_factory = create_session_factory(engine)
    pool = ConnectionPool(PoolConfig(
        max_per_node=config.pool_max_per_node,
        max_total=config.pool_max_total,
        idle_timeout=config.pool_idle_timeout,
        max_lifetime=config.pool_max_lifetime,
    ))
    guard = CommandGuard()
    token_store = ConfirmTokenStore()
    cred_mgr = CredentialManager(config.shuttle_dir)

    @asynccontextmanager
    async def db_session_ctx():
        async with session_factory() as session:
            yield session

    session_mgr = SessionManager(pool, db_session_factory=session_factory)

    # --- FastMCP ---
    mcp = FastMCP(name="shuttle")
    register_tools(
        mcp, pool, guard, token_store, session_mgr,
        db_session_ctx, NodeRepo, cred_mgr=cred_mgr,
    )
    mcp_http = mcp.http_app()

    # --- Combined lifespan ---
    @asynccontextmanager
    async def combined_lifespan(app):
        # Shuttle init
        await init_db(engine)
        async with session_factory() as db_sess:
            await seed_default_rules(db_sess)
            # Register nodes in pool
            node_repo = NodeRepo(db_sess)
            for node in await node_repo.list_all():
                try:
                    pw, pk = None, None
                    decrypted = cred_mgr.decrypt(node.encrypted_credential)
                    if node.auth_type == "password":
                        pw = decrypted
                    else:
                        pk = decrypted
                    info = NodeConnectInfo(
                        node_id=node.name, hostname=node.host, port=node.port,
                        username=node.username, password=pw, private_key=pk,
                    )
                    pool.register_node(info)
                except Exception:
                    pass
        await pool.start_eviction_loop()

        # MCP lifespan
        async with mcp_http.lifespan(mcp_http):
            yield

        # Shutdown
        await pool.close_all()
        await engine.dispose()

    # --- FastAPI ---
    init_db_deps(api_token=api_token, engine=engine, session_factory=session_factory)

    app = FastAPI(
        title="Shuttle",
        version="0.2.0",
        lifespan=combined_lifespan,
        dependencies=[Depends(verify_token)],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )

    # API routes
    from shuttle.web.routes import data, logs, nodes, rules, sessions, settings, stats
    for router in [stats, nodes, rules, sessions, logs, settings, data]:
        app.include_router(router.router, prefix="/api")

    # Mount MCP
    app.mount("/mcp", mcp_http)

    # SPA fallback
    static_dir = Path(__file__).parent.parent / "web" / "static"
    if static_dir.is_dir() and (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True))

    return app
```

- [ ] **Step 2: Add `shuttle serve` CLI command**

In `src/shuttle/cli.py`, replace the `web` command (lines 56-82) with:

```python
@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind address"),
    port: int = typer.Option(9876, "--port", "-p", help="Bind port"),
    db_url: str | None = typer.Option(None, "--db-url", help="Database URL override"),
) -> None:
    """Start Shuttle in service mode (MCP + Web on single HTTP server)."""
    import uvicorn

    from shuttle.core.config import ShuttleConfig

    config = ShuttleConfig()
    config.shuttle_dir.mkdir(parents=True, exist_ok=True)

    # Load or generate API token
    token_path = config.shuttle_dir / "web_token"
    if token_path.exists():
        api_token = token_path.read_text().strip()
    else:
        api_token = secrets.token_urlsafe(32)
        token_path.write_text(api_token)
        token_path.chmod(0o600)

    typer.echo(f"Shuttle service starting at http://{host}:{port}")
    typer.echo(f"  MCP endpoint: http://{host}:{port}/mcp")
    typer.echo(f"  Web panel:    http://{host}:{port}")
    typer.echo(f"  API token:    {api_token}")

    async def _create_and_run():
        from shuttle.mcp.server import create_service_app
        app = await create_service_app(
            host=host, port=port, api_token=api_token, db_url=db_url,
        )
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(_create_and_run())
```

- [ ] **Step 3: Manually test**

```bash
cd /home/local-xiangw/workspace/ssh-mcp && uv run shuttle serve --port 9877
# In another terminal:
curl http://localhost:9877/api/stats
# Should return JSON (without token → 401 if token configured)
```

- [ ] **Step 4: Commit**

```bash
git add src/shuttle/mcp/server.py src/shuttle/cli.py
git commit -m "feat: add shuttle serve command — unified MCP + FastAPI on single ASGI app"
```

---

### Task 9: Frontend — Activity Page + Sidebar Refactor

**Files:**
- Create: `web/src/pages/Activity.tsx`
- Modify: `web/src/App.tsx`
- Modify: `web/src/components/Sidebar.tsx`
- Modify: `web/src/api/client.ts`
- Delete: `web/src/pages/Dashboard.tsx`
- Delete: `web/src/pages/Sessions.tsx`
- Delete: `web/src/pages/SessionDetail.tsx`
- Delete: `web/src/pages/Logs.tsx`

**Note:** Use `/frontend-design` skill when implementing this task.

- [ ] **Step 1: Add useEffectiveRules hook to client.ts**

In `web/src/api/client.ts`, add:

```typescript
export function useEffectiveRules(nodeId: string) {
  return useQuery<RuleResponse[]>({
    queryKey: ["rules", "effective", nodeId],
    queryFn: () => apiFetch(`/rules/effective/${nodeId}`),
    enabled: !!nodeId,
  });
}
```

- [ ] **Step 2: Create Activity page**

Create `web/src/pages/Activity.tsx` — the main view replacing Dashboard, Sessions, Logs, and SessionDetail:

Key features:
- Accepts optional `nodeId` from URL params or sidebar selection
- Uses `useLogs({ node_id: selectedNodeId, page, page_size: 50 })` for data
- Uses `useNodes()` to populate node list in sidebar
- Each log entry: timestamp, command (monospace), exit_code (green ✓ / red ✗), duration, security badge
- Click to expand stdout/stderr
- Pagination at bottom
- Auto-refresh toggle (polling every 5s when enabled)
- Time range filter (today / 7d / 30d / all)
- When no node selected → show all nodes' commands interleaved

- [ ] **Step 3: Refactor Sidebar to node-first**

Update `web/src/components/Sidebar.tsx`:

```tsx
// Top section: logo
// Middle section: node list (from useNodes)
//   - Each node: colored dot (green=recent activity, gray=idle) + name
//   - Click → navigates to /activity/:nodeId
//   - "All Activity" at top of list
//   - "+ Add Node" button at bottom
// Bottom section: static nav
//   - Security Rules → /rules
//   - Settings (opens modal)
```

- [ ] **Step 4: Update App.tsx routes**

```tsx
import { useState } from "react";
import { getToken } from "./api/client";
import Login from "./pages/Login";
import Activity from "./pages/Activity";

// Keep the auth gate from v1:
const [authed, setAuthed] = useState(!!getToken());
if (!authed) return <Login onLogin={() => setAuthed(true)} />;

// Replace all routes:
<Route element={<Layout />}>
  <Route path="/" element={<Navigate to="/activity" replace />} />
  <Route path="/activity" element={<Activity />} />
  <Route path="/activity/:nodeId" element={<Activity />} />
  <Route path="/nodes" element={<Nodes />} />
  <Route path="/rules" element={<Rules />} />
  <Route path="/settings" element={<Settings />} />
</Route>
```

Remove imports for Dashboard, Sessions, SessionDetail, Logs. Keep Login import.

- [ ] **Step 5: Delete old pages**

```bash
rm web/src/pages/Dashboard.tsx web/src/pages/Sessions.tsx web/src/pages/SessionDetail.tsx web/src/pages/Logs.tsx
```

- [ ] **Step 6: Verify build**

```bash
cd /home/local-xiangw/workspace/ssh-mcp/web && npx tsc --noEmit && npm run build
```

- [ ] **Step 7: Commit**

```bash
git add web/src/ && git rm web/src/pages/Dashboard.tsx web/src/pages/Sessions.tsx web/src/pages/SessionDetail.tsx web/src/pages/Logs.tsx
git commit -m "feat(web): replace Dashboard/Sessions/Logs with per-node Activity view"
```

---

### Task 10: Full Test Suite + Cleanup

**Files:**
- Various test files
- Linting

- [ ] **Step 1: Run full Python test suite**

```bash
cd /home/local-xiangw/workspace/ssh-mcp && uv run pytest tests/ -v --tb=short
```

Fix any failures. Common issues:
- Tests importing old `guard.load_rules()` — update to use DB-seeded rules
- Tests using `guard.evaluate()` synchronously — make async
- Tests expecting `web` CLI command — update to `serve`

- [ ] **Step 2: Run linter**

```bash
cd /home/local-xiangw/workspace/ssh-mcp && uv run ruff check src/shuttle/ tests/
```

Fix any issues.

- [ ] **Step 3: Run frontend type check + build**

```bash
cd /home/local-xiangw/workspace/ssh-mcp/web && npx tsc --noEmit && npm run build
```

- [ ] **Step 4: Smoke test service mode**

```bash
uv run python -c "
import asyncio
from httpx import ASGITransport, AsyncClient

async def test():
    from shuttle.mcp.server import create_service_app
    app = await create_service_app(api_token='test123')
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as c:
        # Without token
        r = await c.get('/api/stats')
        assert r.status_code == 401, f'Expected 401 got {r.status_code}'

        # With token
        h = {'Authorization': 'Bearer test123'}
        r = await c.get('/api/stats', headers=h)
        assert r.status_code == 200

        # MCP endpoint exists
        r = await c.post('/mcp', content='{}', headers={'Content-Type': 'application/json'})
        # Should not 404 (may be 400/405 but not 404)
        assert r.status_code != 404

        print('All smoke tests passed!')

asyncio.run(test())
"
```

- [ ] **Step 5: Final commit**

```bash
git add -A && git commit -m "chore: fix all tests and lint for v2 upgrade"
```
