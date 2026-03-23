# Configuration Reference

Shuttle is configured entirely through environment variables (prefixed `SHUTTLE_`) and an optional database-backed settings store. There is no config file to manage — just set the variables you need.

## Environment Variables

All fields in `ShuttleConfig` can be overridden with environment variables prefixed `SHUTTLE_`.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SHUTTLE_SHUTTLE_DIR` | path | `~/.shuttle` | Data directory for DB, credentials, PID file, and token |
| `SHUTTLE_DB_URL` | string | `sqlite+aiosqlite:///~/.shuttle/shuttle.db` | Async SQLAlchemy database URL |
| `SHUTTLE_WEB_HOST` | string | `127.0.0.1` | Bind address for `shuttle serve` |
| `SHUTTLE_WEB_PORT` | int | `9876` | Bind port for `shuttle serve` |
| `SHUTTLE_POOL_MAX_TOTAL` | int | `50` | Maximum total SSH connections across all nodes |
| `SHUTTLE_POOL_MAX_PER_NODE` | int | `5` | Maximum SSH connections per individual node |
| `SHUTTLE_POOL_IDLE_TIMEOUT` | int | `300` | Seconds before an idle connection is evicted |
| `SHUTTLE_POOL_MAX_LIFETIME` | int | `3600` | Maximum lifetime of a connection in seconds |
| `SHUTTLE_POOL_QUEUE_SIZE` | int | `10` | Size of the waiting queue when pool is full |

## Database URL Formats

Shuttle uses SQLAlchemy async drivers. The `SHUTTLE_DB_URL` value must use an async-compatible dialect.

### SQLite (default)

```bash
# Default — no setup required
SHUTTLE_DB_URL="sqlite+aiosqlite:///~/.shuttle/shuttle.db"

# Absolute path
SHUTTLE_DB_URL="sqlite+aiosqlite:////var/lib/shuttle/shuttle.db"
```

SQLite is the default and requires no additional dependencies (aiosqlite is bundled). The `~` in the path is expanded automatically at runtime.

### PostgreSQL

```bash
SHUTTLE_DB_URL="postgresql+asyncpg://user:password@localhost:5432/shuttle"
```

Requires the `asyncpg` driver:

```bash
uv pip install asyncpg
```

### MySQL

```bash
SHUTTLE_DB_URL="mysql+aiomysql://user:password@localhost:3306/shuttle"
```

Requires the `aiomysql` driver:

```bash
uv pip install aiomysql
```

## Connection Pool Parameters

The connection pool manages persistent SSH connections to your nodes. These settings control its behavior.

| Parameter | Default | Recommended Range | Description |
|-----------|---------|-------------------|-------------|
| `POOL_MAX_TOTAL` | 50 | 10 -- 200 | Total connections across all nodes. Set higher if you have many nodes with concurrent AI sessions. |
| `POOL_MAX_PER_NODE` | 5 | 2 -- 20 | Connections per node. Increase for nodes with heavy concurrent usage. |
| `POOL_IDLE_TIMEOUT` | 300s | 60 -- 900 | How long an idle connection stays open. Lower values free resources faster; higher values reduce reconnect overhead. |
| `POOL_MAX_LIFETIME` | 3600s | 600 -- 7200 | Maximum age of a connection regardless of activity. Prevents stale connections from accumulating. |
| `POOL_QUEUE_SIZE` | 10 | 5 -- 50 | How many requests can wait for a connection when the pool is full. |

A background eviction loop runs periodically to close connections that exceed `POOL_IDLE_TIMEOUT` or `POOL_MAX_LIFETIME`.

## Cleanup Policy Settings

Shuttle automatically cleans up old data on startup. These settings are stored in the database (via the Settings page in the web panel or the `app_config` table):

| Key | Default | Description |
|-----|---------|-------------|
| `cleanup_command_logs_days` | 30 | Delete command logs older than this many days |
| `cleanup_closed_sessions_days` | 7 | Delete closed sessions older than this many days |

Cleanup runs at every startup of both `shuttle` (stdio mode) and `shuttle serve` (service mode).

## Data Directory (`~/.shuttle/`)

The default data directory is `~/.shuttle/`. It contains:

| File | Description |
|------|-------------|
| `shuttle.db` | SQLite database (nodes, rules, logs, sessions, config) |
| `shuttle.pid` | PID file for the running Shuttle process |
| `web_token` | Persisted API token for the web panel (created by `shuttle serve`) |
| `credentials.key` | Fernet encryption key for stored SSH credentials |

The directory is created automatically on first run. To use a different location, set `SHUTTLE_SHUTTLE_DIR`.

## Viewing Current Configuration

Use the CLI to display the active configuration:

```bash
shuttle config show
```

This prints a table with the resolved values of all settings, including the Shuttle version, database URL, web bind address, and pool parameters.
