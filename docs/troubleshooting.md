# Troubleshooting

Common issues and solutions when using Shuttle.

## Connection Issues

### "Connection refused" or timeout

**Symptom:** `ssh_run` returns a connection error.

**Checklist:**

1. Verify the node is reachable: `shuttle node test <name>`
1. Check host/port are correct: `shuttle node list`
1. Ensure SSH is running on the remote server
1. Check firewall rules allow port 22 (or your custom port)
1. If using a jump host, verify the jump host itself is reachable first

### "Authentication failed"

**Symptom:** Connection succeeds but authentication is rejected.

**Solutions:**

- **Password auth:** Re-add the node with the correct password: `shuttle node edit <name>`
- **Key auth:** Ensure the private key matches an authorized key on the server
- **Key format:** Shuttle supports OpenSSH format keys. Convert PuTTY keys with `ssh-keygen -i`

### Jump host not working

**Symptom:** Direct connection works but jump host connection fails.

**Checklist:**

1. Verify the jump host node exists and is active: `shuttle node list`
1. Test the jump host directly: `shuttle node test <jump-host-name>`
1. Ensure the jump host can reach the target host on the target port

## MCP Issues

### AI assistant can't find Shuttle tools

**Symptom:** AI says it doesn't have SSH tools available.

**For stdio mode:**

Verify your `.mcp.json`:

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

Ensure `uvx shuttle-mcp --help` works, or run `uv tool install shuttle-mcp` and use `"command": "shuttle"`. See [MCP Setup](mcp-setup.md) for older wheels and `uvx --from` fallback.

**For service (HTTP) mode:**

1. Start the service: `shuttle serve`
1. Verify MCP endpoint responds: `curl http://localhost:9876/mcp/`
1. Configure your AI client:

```json
{
  "mcpServers": {
    "shuttle": {
      "url": "http://localhost:9876/mcp/"
    }
  }
}
```

### Commands blocked unexpectedly

**Symptom:** `ssh_run` returns "BLOCKED" for a command you expect to work.

**Solutions:**

1. Check security rules: open `http://localhost:9876` → Rules page
1. Look for regex patterns that match your command too broadly
1. Use the **Rule Tester** (Rules page → Test button) to see which rule matches
1. Adjust or delete the overly broad rule

### CONFIRM token flow

**Symptom:** Command returns "requires confirmation" with a token.

This is expected for commands matching `confirm`-level rules (e.g., `sudo`, `rm -rf`). The AI should:

1. Show the user the command and ask for confirmation
1. Re-call `ssh_run` with the `confirm_token` parameter

## Web Panel Issues

### Can't access Web UI

**Symptom:** Browser shows connection error at `http://localhost:9876`.

**Checklist:**

1. Ensure `shuttle serve` is running (not just `shuttle` which is stdio-only)
1. Check the port isn't in use: `lsof -i :9876`
1. If binding to a remote server, use `--host 0.0.0.0`

### Token authentication fails

**Symptom:** Login page rejects your token.

The API token is displayed when you run `shuttle serve`:

```
Shuttle service starting at http://127.0.0.1:9876
  API token: do5nLwx1-TOxsyNQZpeQx7TkXh3M8VFEZZT4WNcQZOE
```

The token is stored in `~/.shuttle/web_token`. You can read it directly:

```bash
cat ~/.shuttle/web_token
```

## Database Issues

### Resetting the database

To start fresh, delete the database file:

```bash
rm ~/.shuttle/shuttle.db
```

The database and default security rules are recreated automatically on next startup.

### Using PostgreSQL

For production deployments, switch to PostgreSQL:

```bash
uv pip install asyncpg
SHUTTLE_DB_URL=postgresql+asyncpg://user:pass@host:5432/shuttle shuttle serve
```

## Performance

### Slow command execution

**Possible causes:**

- **Connection pool exhausted:** Increase `SHUTTLE_POOL_MAX_TOTAL` (default: 50)
- **Slow SSH handshake:** Shuttle reuses connections. First command to a node is slower
- **Network latency:** Check with `shuttle node test <name>` which reports latency

### High memory usage

- Reduce `SHUTTLE_POOL_MAX_TOTAL` to limit open SSH connections
- Set `SHUTTLE_POOL_IDLE_TIMEOUT` to close idle connections sooner (default: 300s)
- Old command logs accumulate. Set `cleanup_command_logs_days` in Settings

## Getting Help

- [GitHub Issues](https://github.com/enwaiax/shuttle/issues) — Bug reports and feature requests
- [Documentation](https://enwaiax.github.io/shuttle/) — Full documentation
