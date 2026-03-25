# Example Cursor MCP configs (Shuttle)

These patterns match [docs/mcp-setup.md](../../docs/mcp-setup.md).

## stdio (uvx)

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

## stdio (global `shuttle` on PATH)

After `uv tool install shuttle-mcp`:

```json
{
  "mcpServers": {
    "shuttle": {
      "command": "shuttle"
    }
  }
}
```

## streamable-http

With `shuttle serve` running:

```json
{
  "mcpServers": {
    "shuttle": {
      "url": "http://127.0.0.1:9876/mcp/"
    }
  }
}
```

## Checklist

1. Add SSH nodes: `shuttle node add` (credentials live in Shuttle, not in `mcp.json`).
1. Restart Cursor after editing MCP config.
1. If `uvx shuttle-mcp` fails on an old wheel, use `"args": ["--from", "shuttle-mcp", "shuttle"]` or upgrade Shuttle.

Do **not** commit real passwords into JSON; this repo only ships templates.
