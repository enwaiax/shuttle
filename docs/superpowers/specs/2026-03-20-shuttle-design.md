# Shuttle — SSH MCP Server Design Spec

**Date:** 2026-03-20
**Status:** Approved
**Author:** Claude + enwaiax

---

## 1. Overview

### 1.1 Product Positioning

Shuttle is an AI developer tool that enables Claude Code, Cursor, and other MCP-compatible AI assistants to securely execute commands on remote SSH servers. It provides multi-node management, session isolation, command safety controls, and a web-based control panel.

### 1.2 Brand

- **Name:** Shuttle
- **PyPI package:** `shuttle-mcp`
- **CLI command:** `shuttle`
- **Tagline:** Secure SSH gateway for AI assistants

### 1.3 Key Capabilities

- Multi-node SSH connection management with connection pooling
- SSH Jump Host (bastion) support
- 4-level command security (block / confirm / warn / allow)
- Session isolation with working directory tracking
- Web control panel (configuration, rules, audit logs)
- `uvx shuttle` zero-config startup
- SQLAlchemy ORM with default SQLite, swappable to PostgreSQL/MySQL

---

## 2. Architecture

### 2.1 Dual-Process Model

```
┌──────────────────┐     ┌──────────────────────┐
│  MCP Server      │     │  Web Server           │
│  (stdio process) │     │  (HTTP/WS process)    │
│                  │     │                        │
│  ┌────────────┐  │     │  ┌──────────────────┐ │
│  │ MCP Tools  │  │     │  │ FastAPI + React  │ │
│  └──────┬─────┘  │     │  └────────┬─────────┘ │
│         ▼        │     │           ▼           │
│  ┌────────────┐  │     │  ┌──────────────────┐ │
│  │ Core Engine│  │     │  │ Core Engine      │ │
│  └──────┬─────┘  │     │  └────────┬─────────┘ │
└─────────┼────────┘     └───────────┼───────────┘
          │                          │
          └──────────┬───────────────┘
                     ▼
              ┌──────────┐
              │  SQLite   │
              │  (WAL)    │
              └──────────┘
```

**MCP process** (`uvx shuttle`): Pure stdio, launched by AI clients. Handles command execution, file transfer, session management.

**Web process** (`uvx shuttle web`): Independent HTTP server. Serves React SPA and REST API for configuration, rules, and audit logs.

**Communication:** Shared SQLite database in WAL mode. Both processes read/write the same DB. No direct IPC needed for v1.

### 2.2 Rationale

- stdio isolation prevents HTTP/log output from corrupting MCP JSON protocol
- Independent lifecycles: MCP is ephemeral (started/stopped by AI client), Web can be long-running
- Web crash does not affect MCP operations
- SQLite WAL supports concurrent readers + single writer across processes

---

## 3. Project Structure

```
shuttle/
├── pyproject.toml                  # Package: shuttle-mcp
├── src/
│   └── shuttle/
│       ├── __init__.py
│       ├── __main__.py             # uvx shuttle entry point
│       │
│       ├── core/                   # Shared core engine
│       │   ├── __init__.py
│       │   ├── connection_pool.py  # SSH connection pool
│       │   ├── session.py          # Session management
│       │   ├── security.py         # Command safety layer
│       │   ├── proxy.py            # Jump Host support
│       │   └── config.py           # Global config (Pydantic Settings)
│       │
│       ├── db/                     # Data layer
│       │   ├── __init__.py
│       │   ├── engine.py           # SQLAlchemy async engine
│       │   ├── models.py           # ORM models
│       │   └── repository.py       # Data access layer (CRUD)
│       │
│       ├── mcp/                    # MCP Server process
│       │   ├── __init__.py
│       │   ├── server.py           # FastMCP server setup
│       │   └── tools.py            # MCP tool definitions
│       │
│       ├── web/                    # Web Server process
│       │   ├── __init__.py
│       │   ├── app.py              # FastAPI application
│       │   ├── routes/             # API routes
│       │   │   ├── nodes.py
│       │   │   ├── rules.py
│       │   │   ├── sessions.py
│       │   │   └── settings.py
│       │   └── static/             # React SPA build output
│       │
│       └── cli.py                  # Typer CLI
│
├── web/                            # React frontend source
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── pages/
│       ├── components/
│       └── hooks/
│
└── tests/
    ├── test_core/
    ├── test_mcp/
    ├── test_web/
    └── conftest.py
```

---

## 4. Core Engine

### 4.1 Connection Pool (`core/connection_pool.py`)

Manages SSH connections with pooling, health checks, and automatic eviction.

**Configuration (all user-adjustable):**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_total` | 50 | Global maximum connections |
| `max_per_node` | 5 | Max connections per node |
| `idle_timeout` | 300s | Idle connection eviction |
| `max_lifetime` | 3600s | Max connection age |
| `queue_size` | 10 | Wait queue when pool is full |

**Key behaviors:**
- Lazy connection: no connections at startup, created on first `acquire()`
- SSH multiplexing: single `asyncssh.SSHClientConnection` supports multiple concurrent channels
- Background eviction task: runs every 60s, removes expired and dead connections
- Health check on `acquire()`: if connection is stale, transparently reconnect

**Core interface:**

```python
class ConnectionPool:
    async def acquire(node_id: str) -> PooledConnection
    async def release(conn: PooledConnection)
    async def health_check()
    async def evict_expired()
    async def close_all()
    async def close_node(node_id: str)
```

### 4.2 Session Management (`core/session.py`)

Each MCP conversation gets an isolated session with its own working directory and environment.

```python
class SSHSession:
    session_id: str              # UUID
    node_id: str
    working_directory: str       # Tracked via cd commands
    env_vars: dict[str, str]     # Session-scoped env vars
    status: SessionStatus        # active / idle / closed
    created_at: datetime
    last_active_at: datetime

class SessionManager:
    async def create(node_id: str) -> SSHSession
    async def execute(session_id: str, command: str) -> CommandResult
    async def close(session_id: str)
    async def close_idle(timeout: int)
```

**Working directory tracking:** Commands are wrapped as `cd {working_directory} && {command}`. If the command itself is `cd xxx`, the session's `working_directory` is updated. This makes multi-turn AI conversations feel like a persistent shell.

### 4.3 Command Security (`core/security.py`)

4-level command classification with regex pattern matching:

| Level | Behavior | Default Patterns |
|-------|----------|-----------------|
| **block** | Always reject, no bypass | `rm -rf /`, `mkfs`, `dd if=.* of=/dev/`, fork bombs |
| **confirm** | Require confirmation token, supports bypass | `sudo .*`, `rm -rf .*`, `chmod 777`, `shutdown`, `reboot`, `kill -9` |
| **warn** | Log warning, proceed | `apt install`, `pip install`, `curl .* \| bash` |
| **allow** | Silent pass-through | Everything else |

**Rule evaluation order:** Rules are matched by priority (lower number = higher priority). First match wins. Node-specific rules take precedence over global rules.

**Bypass levels:**
- Single-use: confirm once for this exact command
- Session-level: allow this pattern for the remainder of the session
- Permanent: downgrade rule level via Web panel

### 4.4 Jump Host Support (`core/proxy.py`)

Uses asyncssh's native `tunnel` parameter:

```python
async def connect_with_proxy(node: NodeConfig) -> SSHClientConnection:
    if node.jump_host:
        tunnel = await asyncssh.connect(
            host=jump_host.host, port=jump_host.port,
            username=jump_host.username, ...
        )
        return await asyncssh.connect(
            host=node.host, port=node.port,
            username=node.username, tunnel=tunnel, ...
        )
    return await asyncssh.connect(host=node.host, ...)
```

Jump hosts are themselves nodes in the DB (with a `jump_host_id` foreign key), so they share the same connection pool and configuration UI.

---

## 5. Data Layer

### 5.1 ORM Models

```python
class Node(Base):
    __tablename__ = "nodes"
    id: str                     # UUID PK
    name: str                   # Unique display name
    host: str
    port: int = 22
    username: str
    auth_type: str              # "password" | "key"
    encrypted_credential: str   # Fernet-encrypted
    jump_host_id: str | None    # FK → Node
    tags: JSON                  # ["prod", "gpu"]
    pool_config: JSON           # Per-node pool overrides
    status: str                 # online / offline / unknown
    created_at: datetime
    updated_at: datetime

class SecurityRule(Base):
    __tablename__ = "security_rules"
    id: str                     # UUID PK
    pattern: str                # Regex
    level: str                  # block / confirm / warn / allow
    node_id: str | None         # NULL = global rule
    description: str
    priority: int               # Lower = higher priority
    enabled: bool = True
    created_at: datetime

class Session(Base):
    __tablename__ = "sessions"
    id: str                     # UUID PK
    node_id: str                # FK → Node
    working_directory: str
    env_vars: JSON
    status: str                 # active / idle / closed
    created_at: datetime
    closed_at: datetime | None

class CommandLog(Base):
    __tablename__ = "command_logs"
    id: str                     # UUID PK
    session_id: str             # FK → Session
    node_id: str                # FK → Node (denormalized)
    command: str
    exit_code: int | None
    stdout: str                 # Truncated: first/last 5000 chars if > 64KB
    stderr: str
    security_level: str
    security_rule_id: str | None
    bypassed: bool = False
    duration_ms: int
    executed_at: datetime

class AppConfig(Base):
    __tablename__ = "app_config"
    key: str                    # PK
    value: JSON
    updated_at: datetime
```

### 5.2 Database Engine

```python
def create_db_engine(url: str | None = None):
    db_url = url or f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"
    engine = create_async_engine(db_url)

    if "sqlite" in db_url:
        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(conn, _):
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")

    return engine
```

Default: `sqlite+aiosqlite:///~/.shuttle/shuttle.db`
Configurable: `postgresql+asyncpg://...`, `mysql+aiomysql://...`

### 5.3 Data Directory

```
~/.shuttle/
├── shuttle.db          # SQLite database
├── shuttle.yaml        # Optional config overrides
└── keys/               # Optional key file storage
```

### 5.4 Credential Security

Passwords and key contents encrypted with `cryptography.fernet`. Key derived from machine fingerprint (hostname + MAC hash). Adequate for local single-user scenarios. Users connecting to external databases should use their own secrets management.

---

## 6. MCP Server

### 6.1 Tool Definitions

| Tool | Parameters | Description |
|------|-----------|-------------|
| `ssh_execute` | `command`, `node?`, `session_id?`, `timeout?`, `confirm_token?` | Execute command on remote node |
| `ssh_upload` | `local_path`, `remote_path`, `node` | Upload file via SFTP |
| `ssh_download` | `remote_path`, `local_path`, `node` | Download file via SFTP |
| `ssh_list_nodes` | — | List all nodes with status |
| `ssh_session_start` | `node` | Create new session, return session_id |
| `ssh_session_end` | `session_id` | Close session, cleanup resources |
| `ssh_session_list` | — | List active sessions |

### 6.2 Confirm Mechanism

When a command hits `confirm` level, the MCP tool returns a structured message instead of executing:

```
⚠️ CONFIRMATION REQUIRED
Command: sudo apt update
Matched rule: sudo .* (confirm)
Node: dev-server

To execute, call again with:
  ssh_execute(command='sudo apt update', node='dev-server', confirm_token='abc123')
```

The AI client displays this to the user. Upon user approval, the AI re-calls with the one-time `confirm_token` (60s TTL, bound to specific command + node).

### 6.3 Startup Flow

```
uvx shuttle
  → Check/create ~/.shuttle/
  → Initialize DB (auto-migrate tables)
  → Load node configs from DB
  → Initialize connection pool (lazy, no connections yet)
  → Load security rules from DB
  → Start FastMCP (stdio transport)
  → Ready for MCP calls
```

**No nodes configured?** `ssh_execute` returns a friendly onboarding message directing the user to `shuttle node add` or `shuttle web`.

---

## 7. Web Server

### 7.1 Backend (FastAPI)

```
POST   /api/nodes              Create node
GET    /api/nodes              List nodes (?tag= filter)
GET    /api/nodes/:id          Node detail
PUT    /api/nodes/:id          Update node
DELETE /api/nodes/:id          Delete node
POST   /api/nodes/:id/test     Test connection

GET    /api/rules              List security rules
POST   /api/rules              Create rule
PUT    /api/rules/:id          Update rule
DELETE /api/rules/:id          Delete rule
POST   /api/rules/reorder      Reorder priorities

GET    /api/sessions           List sessions (?status= filter)
GET    /api/sessions/:id       Session detail + command history
DELETE /api/sessions/:id       Close session

GET    /api/logs               Command logs (paginated + filtered)
GET    /api/logs/export        Export logs (JSON/CSV)

GET    /api/settings           Global settings
PUT    /api/settings           Update settings

GET    /api/stats              Dashboard stats

POST   /api/data/export        Full export (nodes + rules + settings)
POST   /api/data/import        Full import
```

SPA fallback: all non-`/api` requests serve `index.html`.

### 7.2 Frontend (React SPA)

**Tech stack:**

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Build | Vite | Fastest SPA bundler |
| UI | Tailwind CSS + Radix UI | Customizable macOS-like styling + accessible primitives |
| State | TanStack Query | Server-state focused, no Redux overhead |
| Router | React Router v7 | Standard choice |
| Table | TanStack Table | Virtual scrolling for logs |
| Charts | Recharts | Dashboard statistics |
| Drag & Drop | dnd-kit | Rule priority reordering |

**Pages:**

1. **Dashboard** — Node status overview, active sessions, today's command count, recent warnings
2. **Nodes** — Node list (card/table view toggle), add/edit/delete/test, tag grouping, jump host config
3. **Security** — Rule list (drag-to-reorder), 4-level color coding, regex editor with live preview, rule tester
4. **Sessions** — Active session list, session detail with command history timeline, manual close
5. **Logs** — Global command history, filter by node/session/level/time, search, export
6. **Settings** — Connection pool params, database config, data import/export, about

**macOS design language:**

- Frosted glass sidebar (`backdrop-filter: blur`)
- Large border-radius (12-16px)
- Neutral gray palette + blue accent
- Subtle shadow layering
- SF Pro / Inter font family
- Smooth transitions (200-300ms ease)

**Build output:** `web/` source builds to `src/shuttle/web/static/` via Vite. Included in the Python package wheel. CI handles the build; end users never need Node.js.

---

## 8. CLI Commands

| Command | Action |
|---------|--------|
| `uvx shuttle` | Start MCP server (stdio, for AI clients) |
| `uvx shuttle web` | Start Web panel (default: http://localhost:9876) |
| `uvx shuttle web --port 8080` | Custom Web port |
| `uvx shuttle node add` | Add SSH node (interactive) |
| `uvx shuttle node list` | List all nodes |
| `uvx shuttle node remove <name>` | Remove node |
| `uvx shuttle config init` | Initialize config (guided) |
| `uvx shuttle config show` | Show current config |
| `uvx shuttle config cleanup` | Run data cleanup |

---

## 9. Performance & Reliability

### 9.1 Performance Targets

| Metric | Target | Mechanism |
|--------|--------|-----------|
| MCP startup | < 500ms | Lazy connections, lightweight init |
| Command latency (pooled) | < 50ms overhead | Connection reuse, zero handshake |
| Command latency (new conn) | < 2s | asyncssh connect + optional jump host |
| Web panel startup | < 1s | Static SPA, FastAPI lightweight |
| API response | < 100ms | Async full-stack + SQLite WAL |
| Log query (100K rows) | < 500ms | SQLite indexes + pagination |
| Concurrent sessions | 50+ | asyncio event loop, no thread overhead |

### 9.2 Optimizations

- **Connection health:** Check staleness on `acquire()`, not via periodic ping. Background eviction scan every 60s for idle connections only.
- **Async log writes:** `ssh_execute` returns immediately; `CommandLog` insertion via `asyncio.create_task`. Non-blocking response path.
- **stdout truncation:** Output > 64KB stored as first + last 5000 chars in DB. Full output returned to MCP client but not persisted. Prevents DB bloat.

### 9.3 Error Recovery

| Scenario | Handling |
|----------|----------|
| SSH connection dropped | Auto-evict from pool, rebuild on next acquire |
| Jump host dropped | Cascade-close all tunneled connections, trigger reconnect |
| DB lock timeout | WAL mode + busy_timeout=5000ms, retry 3x on contention |
| MCP process crash | Sessions marked orphaned, visible in Web panel for cleanup |
| Web process crash | No impact on MCP; restart recovers all state from DB |

### 9.4 Data Cleanup

```yaml
cleanup:
  command_logs_retention: 30d
  closed_sessions_retention: 7d
  orphaned_sessions_cleanup: 1h
```

Runs on Web process startup and via `shuttle config cleanup`.

---

## 10. Dependencies

### Python (Core)

| Package | Version | Purpose |
|---------|---------|---------|
| fastmcp | >= 2.0.0 | MCP protocol framework |
| asyncssh | >= 2.14.0 | SSH connections (async, multiplexing, jump host) |
| fastapi | >= 0.110.0 | Web API server |
| uvicorn | >= 0.27.0 | ASGI server |
| sqlalchemy[asyncio] | >= 2.0.0 | ORM with async support |
| aiosqlite | >= 0.19.0 | SQLite async driver |
| pydantic | >= 2.0.0 | Data validation |
| pydantic-settings | >= 2.0.0 | Configuration management |
| typer | >= 0.12.0 | CLI framework |
| cryptography | >= 41.0.0 | Credential encryption |
| loguru | >= 0.7.0 | Logging |

### JavaScript (Frontend)

| Package | Purpose |
|---------|---------|
| react, react-dom | UI framework |
| vite | Build tool |
| tailwindcss | Styling |
| @radix-ui/* | Accessible UI primitives |
| @tanstack/react-query | Server state management |
| @tanstack/react-table | Virtual scrolling tables |
| react-router | Client-side routing |
| recharts | Dashboard charts |
| @dnd-kit/* | Drag-and-drop rule reordering |

---

## 11. Migration from Current Codebase

The current `fastmcp-ssh-server` codebase will be fully replaced. Key changes:

| Aspect | Current | Shuttle |
|--------|---------|---------|
| Package name | `fastmcp-ssh-server` | `shuttle-mcp` |
| CLI entry | `fastmcp-ssh-server` | `shuttle` |
| Config source | CLI args | SQLite DB + Web UI |
| Connection model | Singleton manager | Connection pool |
| Session support | None | Full session isolation |
| Security | Basic whitelist/blacklist | 4-level with confirm tokens |
| Web UI | None | React SPA control panel |
| Proxy | None | SSH Jump Host |
| Data persistence | None | SQLAlchemy ORM |

Reusable components from current code:
- asyncssh connection logic (refactored into pool)
- Basic command validation patterns (migrated to SecurityRule seeds)
- FastMCP tool registration patterns
- CLI structure (Typer, migrated to new commands)

---

## 12. Future Considerations (Out of Scope for v1)

- SOCKS5/HTTP proxy support
- Web Terminal (xterm.js)
- Multi-user auth on Web panel
- SSH key agent forwarding
- File browser (SFTP directory listing in Web UI)
- Webhook notifications (Slack/Discord on block/confirm events)
- Plugin system for custom security rules
