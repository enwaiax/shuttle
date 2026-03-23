# MCP Client Setup

Shuttle exposes its tools through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). This page covers how to connect Claude Code, Cursor, and other MCP clients to Shuttle in **stdio** and **streamable-http** (`shuttle serve`) modes.

## Package name vs `uvx` (important)

The PyPI package is **`shuttle-mcp`**, but the primary CLI command has always been **`shuttle`**. `uvx <name>` looks for a console script **with the same name as the package**, so:

| Situation | What to use |
|-----------|----------------|
| **Current PyPI releases** (with `shuttle-mcp` script; see `pyproject.toml`) | `"command": "uvx", "args": ["shuttle-mcp"]` or run `uvx shuttle-mcp` |
| **Very old wheels** (no `shuttle-mcp` entry point) | `"args": ["--from", "shuttle-mcp", "shuttle"]` |
| **After `uv tool install shuttle-mcp`** (CLI on `PATH`) | `"command": "shuttle"` (no `uvx`) |

This is a **small usability / documentation issue**, not a security or protocol bug. Prefer **`uvx shuttle-mcp`** in MCP config when you do not install globally; use **`--from shuttle-mcp shuttle`** only if your PyPI wheel predates the `shuttle-mcp` console script.

## Quick copy-paste: stdio vs serve

### stdio (AI client spawns Shuttle)

Use the same JSON in **Claude Code** (`.mcp.json` / `~/.mcp.json`) or **Cursor** (`.cursor/mcp.json` or Settings → MCP).

```json
{
  "mcpServers": {
    "shuttle": {
      "command": "uvx",
      "args": ["shuttle-mcp"]
    }
  }
}
```

**Cursor UI:** **Command** = `uvx`, **Arguments** = `shuttle-mcp` (single arg). If your installed package is too old, use three args: `--from`, `shuttle-mcp`, `shuttle`.

**Claude Code:** there is no universal “one button” in the repo; paste the JSON into the project or user `mcp.json` and restart the client.

### streamable-http (`shuttle serve`)

1. Start the service: `shuttle serve` (note host/port and the **API token** printed for the **web panel** only).
2. Point the MCP client at the HTTP endpoint (trailing slash required):

```json
{
  "mcpServers": {
    "shuttle": {
      "url": "http://127.0.0.1:9876/mcp/"
    }
  }
}
```

**Cursor UI:** add server type **URL**, paste `http://127.0.0.1:9876/mcp/`. The web UI token does **not** go here; `/mcp/` is not gated by that token.

Remote machine: use `http://<host>:<port>/mcp/` and ensure firewall / `--host 0.0.0.0` as needed.

## Transport Modes

| Mode | How you start Shuttle | Transport | Web UI | Best for |
|------|------------------------|-----------|--------|----------|
| **stdio** | AI runs `uvx … shuttle` or `shuttle` | stdin/stdout | No | Single-user, client manages process |
| **streamable-http** | `shuttle serve` | HTTP `…/mcp/` | Yes | Long-running service, audit panel, multiple clients |

Both modes can share the same database; see [Configuration](configuration.md) for `SHUTTLE_DB_URL`.

## Claude Code

### stdio

Create or edit `.mcp.json` in the project root or `~/.mcp.json`:

```json
{
  "mcpServers": {
    "shuttle": {
      "command": "uvx",
      "args": ["shuttle-mcp"]
    }
  }
}
```

If `shuttle` is on `PATH` after `uv tool install shuttle-mcp`:

```json
{
  "mcpServers": {
    "shuttle": {
      "command": "shuttle"
    }
  }
}
```

### streamable-http

```bash
shuttle serve
```

```json
{
  "mcpServers": {
    "shuttle": {
      "url": "http://localhost:9876/mcp/"
    }
  }
}
```

Note the trailing slash on `/mcp/`. Requests to `/mcp` without slash get a 307 redirect.

## Cursor

### stdio

- **Settings → MCP → Add server** (wording may vary by Cursor version):
  - **Name:** `shuttle`
  - **Type:** Command (stdio)
  - **Command:** `uvx`
  - **Arguments:** `shuttle-mcp` (or `--from`, `shuttle-mcp`, `shuttle` on old wheels)

Or edit **`.cursor/mcp.json`** (project) or the user-level MCP JSON your build expects:

```json
{
  "mcpServers": {
    "shuttle": {
      "command": "uvx",
      "args": ["shuttle-mcp"]
    }
  }
}
```

### streamable-http

1. Run `shuttle serve`.
2. **Type:** URL
3. **URL:** `http://localhost:9876/mcp/`

```json
{
  "mcpServers": {
    "shuttle": {
      "url": "http://localhost:9876/mcp/"
    }
  }
}
```

## Environment variable passthrough

### `SHUTTLE_DB_URL`

```json
{
  "mcpServers": {
    "shuttle": {
      "command": "uvx",
      "args": ["shuttle-mcp"],
      "env": {
        "SHUTTLE_DB_URL": "postgresql+asyncpg://user:pass@localhost:5432/shuttle"
      }
    }
  }
}
```

### Multiple variables

```json
{
  "mcpServers": {
    "shuttle": {
      "command": "uvx",
      "args": ["shuttle-mcp"],
      "env": {
        "SHUTTLE_DB_URL": "sqlite+aiosqlite:////shared/shuttle.db",
        "SHUTTLE_POOL_MAX_TOTAL": "100",
        "SHUTTLE_POOL_MAX_PER_NODE": "10"
      }
    }
  }
}
```

See [Configuration](configuration.md) for all `SHUTTLE_*` variables.

## Troubleshooting

### "Connection refused" (streamable-http)

- Confirm `shuttle serve` is running and the port matches the URL.
- Default bind is `127.0.0.1`; use `--host 0.0.0.0` if the client runs on another host.

### MCP tools missing (stdio)

- Valid JSON, no trailing commas (unless your client supports JSONC).
- Terminal check: `uvx shuttle-mcp --help` should print Typer help.
- On wheels without the `shuttle-mcp` script, use `uvx --from shuttle-mcp shuttle --help` instead.

### Web panel "Invalid or missing token"

- Applies to **Web/API**, not to `/mcp/`. Use the token from startup output or `~/.shuttle/web_token`.

### SQLite database locked

- Avoid running **stdio** and **`shuttle serve`** against the same SQLite file at once, or use PostgreSQL for `SHUTTLE_DB_URL`.

### Commands hang

- `shuttle node test <name>`, pool limits in [Configuration](configuration.md).
