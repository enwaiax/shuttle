# Cursor MCP — Shuttle (stdio & serve)

This folder contains **templates** for connecting [Cursor](https://cursor.com) to **Shuttle**. Shuttle is configured via `shuttle node add` (not via inline SSH flags in `mcp.json`).

**Authoritative doc:** [docs/mcp-setup.md](../../docs/mcp-setup.md) (Claude Code, Cursor, stdio, `shuttle serve`, env vars, troubleshooting).

## stdio (recommended for single machine)

Cursor spawns Shuttle as a child process. Use **`command` + `args`** (do not use a single `uvx shuttle-mcp` string — see package vs CLI note in `mcp-setup.md`).

**Project file:** `.cursor/mcp.json`
**Or** user-level path (varies by OS; check Cursor Settings → MCP).

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

**Cursor Settings → MCP:** Command = `uvx`, arguments = `shuttle-mcp`. On very old PyPI wheels, use `--from`, `shuttle-mcp`, `shuttle`.

After nodes exist (`shuttle node add`), restart Cursor and ask the AI to use Shuttle tools (e.g. `ssh_list_nodes`).

## streamable-http (`shuttle serve`)

1. Terminal: `shuttle serve` (note port; default `9876`).
2. Cursor: add MCP server type **URL**:

```json
{
  "mcpServers": {
    "shuttle": {
      "url": "http://127.0.0.1:9876/mcp/"
    }
  }
}
```

Trailing **`/`** on `/mcp/` is required. The **web panel** Bearer token is **not** used for `/mcp/`.

## Files here

| File | Purpose |
|------|---------|
| `basic-config.json` | Minimal stdio template |
| `serve-config.json` | Minimal HTTP template (`shuttle serve`) |
| `setup-cursor-mcp.sh` | Writes a **stdio** `.cursor/mcp.json` in the repo root |

## Legacy

Older samples in git history referred to `fastmcp-ssh-server`; they are **not** Shuttle. Ignore any third-party gist that still uses that name.
