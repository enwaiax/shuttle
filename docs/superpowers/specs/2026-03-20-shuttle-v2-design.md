# Shuttle v2 — Design Spec

**Date:** 2026-03-20
**Status:** Draft
**Supersedes:** `2026-03-20-shuttle-design.md` (v1)

---

## 1. Product Definition

### What is Shuttle

Shuttle is an MCP server that bridges AI assistants (Claude Code, Cursor, etc.) to remote SSH servers. AI operates remote machines through Shuttle; Shuttle ensures this is **safe, manageable, and auditable**.

```
Developer ↔ AI Assistant ↔ Shuttle (MCP) ↔ SSH ↔ Remote Servers
```

Shuttle is not an SSH client for humans. Humans don't SSH through Shuttle. AI does.

### Three Core Capabilities

1. **Connection Management** — multi-node SSH with connection pooling, session isolation, jump host support
2. **Security Control** — 4-level command rules (block/confirm/warn/allow), global defaults + per-node overrides
3. **Command Audit** — every command logged to DB with full context, queryable per node and time range

### Target User

A developer working with AI coding assistants who has one or more remote servers (GPU machines, dev servers, staging environments). Single-user first; shared database enables team use later.

---

## 2. Architecture

### Two Running Modes

**Mode 1: CLI (stdio)**

```
.mcp.json: {"shuttle": {"command": "uvx", "args": ["shuttle"]}}
```

- AI client spawns and manages the process
- Reads node config from DB, executes commands, logs to DB
- No HTTP server, no Web UI
- Lifecycle tied to AI client session

**Mode 2: Service (streamable-http)**

```bash
uvx shuttle serve --port 9876
```

```
.mcp.json: {"shuttle": {"url": "http://localhost:9876/mcp"}}
```

- Independent HTTP service: MCP + API + Web on single port
- AI connects via streamable-http transport
- Browser opens `localhost:9876` for Web UI
- Lifecycle independent of AI client

### Single-Process Architecture (Service Mode)

```
uvx shuttle serve (:9876)
│
├── /mcp             → FastMCP streamable-http (AI clients)
├── /api/*           → FastAPI REST (Web panel backend)
├── /                → React SPA (Web panel frontend)
│
└── Shared Runtime (single process, single event loop)
    ├── ConnectionPool
    ├── SessionManager
    ├── CommandGuard
    └── SQLAlchemy Engine
```

**ASGI Mount Strategy:** FastAPI is the root ASGI application. FastMCP's streamable-http app is mounted as a sub-application at `/mcp`:

```python
from fastapi import FastAPI
from fastmcp import FastMCP

# 1. Create core objects (single instances)
engine = create_db_engine(db_url)
pool = ConnectionPool(...)
guard = CommandGuard(...)
session_mgr = SessionManager(pool, ...)

# 2. Create FastMCP with tools (references shared core objects)
mcp = FastMCP("shuttle")
register_tools(mcp, pool, guard, ...)

# 3. Create FastAPI app (references same shared core objects via deps)
app = create_app(engine, pool, guard, session_mgr)

# 4. Mount FastMCP's HTTP app inside FastAPI
mcp_http = mcp.http_app()  # Returns StarletteWithLifespan
app.mount("/mcp", mcp_http)

# 5. uvicorn runs the single FastAPI app
uvicorn.run(app, host=host, port=port)
```

**Single engine, single pool.** Both FastMCP tools and FastAPI routes use the same `engine`, `pool`, `guard`, and `session_mgr` instances — passed via constructor/closure, not module-level globals. The v1 `deps.py` module-level globals are refactored to accept injected instances in service mode.

**Lifespan:** `mcp.http_app()` returns a `StarletteWithLifespan` that has its own lifespan for MCP session management. FastAPI's lifespan handles Shuttle-specific init (DB tables, eviction loop, rule seeding). Both lifespans must run. Use FastAPI's lifespan to also invoke the MCP sub-app's lifespan:

```python
@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    # Shuttle init
    await init_db(engine)
    await seed_default_rules(...)
    pool.start_eviction_loop()

    # MCP sub-app lifespan
    async with mcp_http.lifespan(mcp_http):
        yield
```

### Shared Database

Both modes read/write the same database. Default: `~/.shuttle/shuttle.db` (SQLite with WAL mode). Configurable via environment variable or CLI flag:

```bash
# PostgreSQL
SHUTTLE_DB_URL=postgresql+asyncpg://user:pass@host:5432/shuttle uvx shuttle serve

# MySQL
SHUTTLE_DB_URL=mysql+aiomysql://user:pass@host:3306/shuttle uvx shuttle
```

SQLAlchemy ORM with async drivers. SQLite is zero-dependency; PostgreSQL/MySQL require optional extras:

```toml
[project.optional-dependencies]
postgres = ["asyncpg>=0.29.0"]
mysql = ["aiomysql>=0.2.0"]
```

Commands logged in stdio mode are visible in Web UI when service mode is started (same DB).

---

## 3. CLI Commands

```
uvx shuttle                          # Mode 1: stdio MCP (no Web)
uvx shuttle serve                    # Mode 2: HTTP service (MCP + Web)
uvx shuttle serve --port 8080        # Custom port (default: 9876)
uvx shuttle serve --host 0.0.0.0     # Bind to all interfaces (cloud deploy)
uvx shuttle serve --db-url <url>     # Custom database URL

shuttle node add                     # Interactive: add SSH node
shuttle node list                    # List all nodes with status
shuttle node test <name>             # Test SSH connectivity
shuttle node remove <name>           # Remove a node
shuttle node edit <name>             # Interactive edit (preserved from v1)

shuttle config show                  # Display current configuration
```

`shuttle web` is removed. Web UI is only available via `shuttle serve`.

---

## 4. MCP Tools

| Tool | Description | New in v2 |
|------|-------------|-----------|
| `ssh_execute` | Execute command on a node | |
| `ssh_upload` | SFTP upload | |
| `ssh_download` | SFTP download | |
| `ssh_list_nodes` | List all configured nodes | |
| `ssh_session_start` | Create stateful session | |
| `ssh_session_end` | Close session | |
| `ssh_session_list` | List active sessions | |
| **`ssh_add_node`** | Add a new SSH node | ✓ |
| **`ssh_remove_node`** | Remove a node by name | ✓ |

### ssh_add_node

```python
async def ssh_add_node(
    name: str,
    host: str,
    port: int = 22,
    username: str = "",
    password: str | None = None,
    private_key: str | None = None,
    jump_host: str | None = None,  # name of existing node to use as jump host
    tags: list[str] | None = None,
) -> str
```

Encrypts credentials via CredentialManager, saves to DB. In service mode, also registers in the shared ConnectionPool immediately. In stdio mode, the pool is local to the process — the new node is registered in the current pool and persisted to DB for future sessions. Returns confirmation message.

### ssh_remove_node

```python
async def ssh_remove_node(name: str) -> str
```

Closes idle connections for this node via `pool.close_node()`. Active (checked-out) connections are discarded on release. Removes from pool registry, deletes from DB. Returns confirmation.

---

## 5. Security Rules

### 4-Level System

| Level | Behavior | Example |
|-------|----------|---------|
| **block** | Reject immediately, return error | `rm -rf /`, `mkfs`, fork bomb |
| **confirm** | Return confirmation prompt; AI client shows to user; re-call with token to execute | `sudo .*`, `rm -rf`, `chmod 777`, `shutdown` |
| **warn** | Execute but log as warning | `apt install`, `pip install`, `curl | bash` |
| **allow** | Execute silently | Everything else |

### Per-Node Inheritance

Rules cascade: **global defaults → node-specific overrides**.

```
Global Defaults
├── block: rm -rf /
├── confirm: sudo .*
├── warn: pip install

Node: gpu-server (inherits + overrides)
├── [inherited] block: rm -rf /
├── [override] sudo .* → allow        # trusted environment
├── [node-only] confirm: kill -9       # extra caution on GPU jobs
```

Data model:

```python
class SecurityRule(Base):
    id: str
    pattern: str           # regex
    level: str             # block / confirm / warn / allow
    node_id: str | None    # NULL = global default
    source_rule_id: str | None  # if overridden from a default rule
    description: str | None
    priority: int
    enabled: bool
    created_at: datetime
```

**Evaluation strategy:** CommandGuard queries the DB on each `evaluate()` call to load the effective rule set (global + node-specific). This avoids stale in-memory caches — when rules are edited via Web UI or MCP, the next command evaluation sees the change immediately. The query is lightweight (typically <20 rules) and async, so latency impact is negligible.

Node-specific rules take precedence over global defaults when both match the same pattern (same pattern string, lower priority number wins; if tied, node-specific wins).

### Confirm Flow

```
AI calls ssh_execute("sudo apt update", node="prod")
  → CommandGuard: matches "sudo .*" → confirm
  → Return: "⚠️ CONFIRMATION REQUIRED\n...\nRe-call with confirm_token='abc123'"
  → AI client shows this to the user
  → User approves in terminal
  → AI calls ssh_execute("sudo apt update", node="prod", confirm_token="abc123")
  → Token validated (one-time, 300s TTL) → execute
```

No web-based approval. Confirmation happens in the AI client's terminal.

---

## 6. Command Audit

Every `ssh_execute` call writes a `CommandLog` record to the database:

```python
class CommandLog(Base):
    id: str
    session_id: str | None
    node_id: str
    command: str
    exit_code: int | None
    stdout: str | None       # truncated to 64KB for DB storage
    stderr: str | None
    security_level: str | None
    security_rule_id: str | None
    bypassed: bool
    duration_ms: int | None
    executed_at: datetime
```

Logging is inline (`await log_repo.create(...)`) within the command execution flow. This ensures logs are persisted before the response is returned. The latency overhead is minimal for async SQLite/PostgreSQL writes.

Full command output is returned to the AI client. Only truncated output (first N bytes + `[truncated]` marker if >64KB) is persisted to DB to prevent bloat.

### Cleanup Policy

Configurable retention via settings (stored in `app_config` table):

```
command_logs_retention: 30 days (default)
closed_sessions_retention: 7 days (default)
```

---

## 7. Web UI

### Purpose

The Web UI serves two functions:

1. **Audit** — Browse command logs per node, filter by time range, review what AI did
2. **Manage** — Configure nodes (add/edit/remove), configure security rules (global defaults + per-node overrides), adjust settings

The Web UI does not execute commands, does not provide a terminal, and does not do real-time streaming. It reads from the database.

### Tech Stack

- **Backend:** FastAPI (shares ASGI app with FastMCP in service mode)
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS 4, Radix UI, Lucide icons, TanStack Query
- **Design:** macOS-inspired — system font stack, subtle shadows, rounded corners, restrained palette
- **Packaging:** React builds to `src/shuttle/web/static/`, served by FastAPI as static fallback

### Views

**3 views, not 8 pages:**

#### View 1: Activity (default)

Per-node command log browser. This is the main view.

- Left sidebar: node list with status indicators (online/offline based on last command)
- Click a node → show that node's command history
- Click "All" → show all nodes' commands interleaved
- Each log entry: timestamp, command, exit code, duration, security level badge
- Expand to see stdout/stderr
- Filter by time range
- Paginated (50 per page default)
- Refresh button (or auto-refresh toggle, polling /api/logs)

#### View 2: Security Rules

Global default rules + per-node overrides.

- Default rules table: pattern, level (color-coded badge), description, priority, enabled toggle
- Add / edit / delete rules
- Per-node section: select a node → see effective rules (inherited + overrides)
- "Override for this node" action: copies a default rule, lets you change the level
- "Add rule for this node" action: creates a node-specific rule
- Drag-to-reorder (or up/down buttons for v1)

#### View 3: Settings (slide-out or modal)

- Connection pool: max_total, max_per_node, idle_timeout, max_lifetime
- Cleanup: command_logs_days, closed_sessions_days
- Database URL (read-only display)
- Save button

**Node management** is in the sidebar, not a separate view:

- "+" button opens Add Node form (dialog)
- Right-click or menu on a node → Edit / Remove / Test Connection
- Node edit is a dialog, not a separate page

### API Endpoints

Mostly preserved from v1:

```
# Nodes
GET    /api/nodes              # List (with ?tag= filter)
POST   /api/nodes              # Create
GET    /api/nodes/:id          # Get
PUT    /api/nodes/:id          # Update
DELETE /api/nodes/:id          # Delete
POST   /api/nodes/:id/test     # Test connection

# Security Rules
GET    /api/rules              # List (ordered by priority)
POST   /api/rules              # Create
PUT    /api/rules/:id          # Update
DELETE /api/rules/:id          # Delete
POST   /api/rules/reorder      # Reorder priorities
GET    /api/rules/effective/:node_id  # NEW: Get effective rules for a node

# Command Logs
GET    /api/logs               # Paginated list (?page, ?page_size, ?node_id, ?session_id)
GET    /api/logs/export        # Export as JSON or CSV

# Settings
GET    /api/settings           # Get
PUT    /api/settings           # Update

# Stats
GET    /api/stats              # Dashboard counts

# Data
POST   /api/data/export        # Full export (nodes + rules + settings)
POST   /api/data/import        # Import
```

New endpoint: `GET /api/rules/effective/:node_id` returns the merged rule list (global defaults + node overrides) for a specific node.

### Authentication

Bearer token required for all `/api/*` routes in service mode.

- Token generated on first `shuttle serve` run, saved to `~/.shuttle/web_token`
- Displayed in terminal output on startup
- Frontend: Login page prompts for token, stores in localStorage
- `verify_token` dependency skipped when no token configured (e.g., tests)

---

## 8. Core Engine (Unchanged from v1)

These modules are stable and require no changes:

| Module | Responsibility |
|--------|---------------|
| `core/connection_pool.py` | SSH connection pooling with per-node limits, TTL eviction |
| `core/session.py` | Session isolation, working directory tracking |
| `core/security.py` | CommandGuard, SecurityLevel, ConfirmTokenStore |
| `core/proxy.py` | Jump host / SSH tunneling via asyncssh |
| `core/credentials.py` | Fernet encryption for stored passwords/keys |
| `core/config.py` | Pydantic Settings with `SHUTTLE_` env prefix |
| `db/models.py` | SQLAlchemy ORM models |
| `db/repository.py` | CRUD repositories |
| `db/engine.py` | Async engine creation, SQLite WAL pragma |
| `db/seeds.py` | Default security rule seeds |

### Changes to Core

1. **`core/security.py`** — Refactor `CommandGuard.evaluate()`:
   - Change from `def evaluate(...)` to `async def evaluate(...)` (sync → async)
   - Add `db_session: AsyncSession` parameter
   - Query rules from DB per call (global + node-specific), instead of in-memory cache
   - Remove `load_rules()` method; rules are always live from DB
   - **All callers must be updated:** `_execute_command_logic()` in `tools.py` and all tests that call `evaluate()`

2. **`db/models.py`** — Add `source_rule_id` nullable field to `SecurityRule` for tracking which default rule was overridden. **Schema migration:** Since `Base.metadata.create_all()` does not add columns to existing tables, add an explicit migration in `init_db()` that checks for the column and runs `ALTER TABLE security_rules ADD COLUMN source_rule_id VARCHAR(36)` if missing. This is safe for SQLite and PostgreSQL.

3. **`db/repository.py`** — Add `source_rule_id` parameter to `RuleRepo.create()`. Add `RuleRepo.list_effective(node_id)` method that returns merged global + node-specific rules ordered by priority.

4. **`web/schemas.py`** — Add `source_rule_id: str | None` to `RuleCreate`, `RuleResponse`.

5. **`mcp/tools.py`** — Fix pre-existing bug: `CommandLog.node_id` must store the node UUID, not the node name string. Resolve node name to `(name, uuid)` early; use name for pool/guard, uuid for DB logging.

---

## 9. Project Structure

```
src/shuttle/
├── __init__.py
├── __main__.py
├── cli.py                    # Typer: shuttle, shuttle serve, shuttle node *, shuttle config
├── core/
│   ├── config.py
│   ├── connection_pool.py
│   ├── credentials.py
│   ├── proxy.py
│   ├── security.py           # + per-node inheritance
│   └── session.py
├── db/
│   ├── engine.py
│   ├── models.py             # + source_rule_id on SecurityRule
│   ├── repository.py
│   └── seeds.py
├── mcp/
│   ├── server.py             # + streamable-http mode, ASGI mount
│   └── tools.py              # + ssh_add_node, ssh_remove_node
└── web/
    ├── app.py                # FastAPI factory, mounts FastMCP in service mode
    ├── deps.py               # DB session, token auth
    ├── schemas.py
    ├── routes/
    │   ├── nodes.py
    │   ├── rules.py          # + effective rules endpoint
    │   ├── sessions.py
    │   ├── logs.py
    │   ├── settings.py
    │   ├── stats.py
    │   └── data.py
    └── static/               # React build output

web/                          # React source
├── src/
│   ├── App.tsx
│   ├── api/client.ts
│   ├── types/index.ts
│   ├── components/           # Layout, Sidebar, Badge, DataTable, etc.
│   └── pages/
│       ├── Login.tsx
│       ├── Activity.tsx      # Per-node command log browser (main view)
│       ├── Rules.tsx         # Security rules with inheritance
│       ├── RuleForm.tsx
│       ├── NodeForm.tsx      # Add/edit node dialog
│       └── Settings.tsx      # Settings modal
```

---

## 10. Migration from v1

### What stays
- All `core/*` modules (connection pool, session, proxy, credentials, config)
- All `db/*` modules (models, repository, engine, seeds)
- MCP tools (ssh_execute, ssh_upload, ssh_download, ssh_list_nodes, ssh_session_*)
- Web API routes (nodes, rules, sessions, logs, settings, stats, data)
- Web schemas
- Existing Python tests (with updates for changed interfaces)
- React components: Badge, DataTable, ConfirmDialog, EmptyState, Layout, Sidebar
- React pages: Login, NodeForm, RuleForm, Settings
- Existing `~/.shuttle/web_token` files are reused automatically

### What changes
- `cli.py` — remove `shuttle web`, add `shuttle serve` (wires FastMCP + FastAPI into single ASGI app)
- `mcp/server.py` — add streamable-http startup, return ASGI sub-app for mounting
- `mcp/tools.py` — add ssh_add_node, ssh_remove_node; fix node_id bug: resolve node name to `(node_name, node_uuid)` tuple early in `_execute_command_logic()`. Use `node_name` for pool/guard/token_store (they are keyed by name). Use `node_uuid` for `CommandLog.node_id` (FK to nodes.id). This keeps the pool's name-based keying intact while fixing the DB FK violation.
- `web/app.py` — accept injected core objects; mount FastMCP sub-app in service mode
- `web/deps.py` — refactor from module-level globals to accept injected engine/pool
- `core/security.py` — refactor evaluate() to query DB per call (live rules, no cache)
- `db/models.py` — add source_rule_id to SecurityRule + migration logic
- `db/repository.py` — add RuleRepo.list_effective(node_id), add source_rule_id to RuleRepo.create()
- `web/schemas.py` — add source_rule_id to RuleCreate/RuleResponse
- `web/routes/rules.py` — add GET /api/rules/effective/:node_id
- `db/models.py` — reconcile tags: change `Node.tags` type annotation from `dict | None` to `list | None` (JSON column stays the same — it's schema-agnostic). Update `NodeRepo.list_all()` filter to only handle lists: `tag in (n.tags or [])`. Existing rows with dict-format tags are treated as empty (no migration needed — this is a new product with minimal data).

### What's new (frontend)
- `pages/Activity.tsx` — replaces Dashboard + Sessions + Logs as the main view
- `pages/Login.tsx` — already built in v1
- Sidebar refactor — node list with status, click to filter activity

### What's removed
- `shuttle web` CLI command (replaced by `shuttle serve`)
- Separate Dashboard, Sessions, Logs pages (merged into Activity)
- Independent web process concept
- In-memory rule caching in CommandGuard (replaced by per-call DB query)

### Known v1 bugs fixed in v2
- `CommandLog.node_id` stored node name instead of UUID (FK violation on PostgreSQL)
- `Node.tags` stored as `dict` wrapper but API expected `list` (inconsistent serialization)
