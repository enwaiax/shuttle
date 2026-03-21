# MCP Client Setup

Shuttle exposes its tools through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). This page covers how to connect Claude Code, Cursor, and other MCP clients to Shuttle in both stdio and streamable-http modes.

## Transport Modes

| Mode | Command | Transport | Web UI | Best for |
|------|---------|-----------|--------|----------|
| **stdio** | `shuttle` | stdio (stdin/stdout) | No | Single-user, AI client manages the process lifecycle |
| **streamable-http** | `shuttle serve` | HTTP (`/mcp/`) | Yes | Multi-user, persistent service, audit via web panel |

Both modes share the same SQLite database, so commands logged in stdio mode are visible in the web panel when you switch to service mode.

## Claude Code

### stdio mode

Create or edit `.mcp.json` in your project root (or `~/.mcp.json` for global config):

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

If you installed with `pip` instead of `uvx`:

```json
{
  "mcpServers": {
    "shuttle": {
      "command": "shuttle"
    }
  }
}
```

### streamable-http mode

First, start the Shuttle service:

```bash
shuttle serve
```

Then configure `.mcp.json`:

```json
{
  "mcpServers": {
    "shuttle": {
      "url": "http://localhost:9876/mcp/"
    }
  }
}
```

Note the trailing slash on `/mcp/` — it is required. Requests to `/mcp` (without the slash) are redirected with a 307.

## Cursor

### stdio mode

Open Cursor Settings, navigate to the MCP section, and add a new server:

- **Name**: `shuttle`
- **Type**: `command`
- **Command**: `uvx shuttle-mcp`

Or edit `.cursor/mcp.json` in your project:

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

### streamable-http mode

Start the service with `shuttle serve`, then configure in Cursor:

- **Name**: `shuttle`
- **Type**: `url`
- **URL**: `http://localhost:9876/mcp/`

Or in `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "shuttle": {
      "url": "http://localhost:9876/mcp/"
    }
  }
}
```

## Environment Variable Passthrough

You can pass environment variables through your MCP config to override Shuttle settings. This is useful for pointing Shuttle at a different database or port without changing your system environment.

### Passing `SHUTTLE_DB_URL`

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

### Passing multiple variables

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

See [Configuration](configuration.md) for the full list of `SHUTTLE_*` variables.

## Troubleshooting

### "Connection refused" when using streamable-http

- Verify `shuttle serve` is running. Check for the process: `ps aux | grep shuttle`.
- Confirm the port matches. Default is `9876`. If you used `--port`, update the URL accordingly.
- If binding to `127.0.0.1` (default), the client must be on the same machine. Use `--host 0.0.0.0` to listen on all interfaces.

### MCP tools not appearing in Claude Code / Cursor

- Check that `.mcp.json` is valid JSON (no trailing commas, no comments in non-JSONC files).
- For stdio mode, verify that the `shuttle` or `uvx` command is on your `PATH`. Run `which shuttle` or `which uvx` to confirm.
- Restart the AI client after editing `.mcp.json`.

### "Invalid or missing token" errors on the web panel

- The web panel API routes require a Bearer token. This does **not** affect MCP transport — the `/mcp/` endpoint is not gated by the web token.
- If the web panel rejects your token, check `~/.shuttle/web_token` for the current value. Delete the file and restart `shuttle serve` to generate a new one.

### Database locked (SQLite)

- SQLite does not support concurrent writes from multiple processes. If you run both `shuttle` (stdio) and `shuttle serve` simultaneously, you may see locking errors.
- Solution: switch to PostgreSQL (`SHUTTLE_DB_URL=postgresql+asyncpg://...`) for multi-process setups, or run only one mode at a time.

### Commands hang or time out

- Check SSH connectivity to the target node: `shuttle node test <name>`.
- Verify the connection pool is not exhausted. Default max is 50 total / 5 per node. Increase via `SHUTTLE_POOL_MAX_TOTAL` and `SHUTTLE_POOL_MAX_PER_NODE`.
- Check `SHUTTLE_POOL_IDLE_TIMEOUT` — if set very low, connections may be evicted between rapid commands, causing reconnect delays.
