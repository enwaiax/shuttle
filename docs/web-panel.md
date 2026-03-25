# Web Panel

The Shuttle web panel is a browser-based UI for monitoring and managing your SSH gateway. It runs alongside the MCP endpoint in service mode on the same port.

## Starting the Web Panel

```bash
shuttle serve
```

This starts both the MCP endpoint (`/mcp/`) and the web panel (`/`) on `http://localhost:9876`.

### Custom host and port

```bash
shuttle serve --host 0.0.0.0 --port 8080
```

On startup, Shuttle prints a panel with the MCP endpoint URL, web panel URL, and API token:

```
╭──────────── Shuttle ────────────╮
│  MCP endpoint  http://127.0.0.1:9876/mcp   │
│  Web panel     http://127.0.0.1:9876        │
│  API token     <your-token-here>            │
╰──────────── http://127.0.0.1:9876 ──────────╯
```

## Token Authentication

The web panel API is protected by a Bearer token. The token is:

- **Auto-generated** on first run of `shuttle serve` and saved to `~/.shuttle/web_token`.
- **Persisted** across restarts — the same token is reused until you delete the file.
- **Displayed** in the terminal output when the server starts.

To authenticate in the web UI, enter the token when prompted. The frontend stores it in the browser and sends it as an `Authorization: Bearer <token>` header on every API request.

To reset the token, delete `~/.shuttle/web_token` and restart `shuttle serve`.

Note: The `/mcp/` endpoint is **not** gated by this token. MCP clients connect without authentication.

## Overview Page

The Overview page is the landing page of the web panel. It shows:

- **Node cards** — One card per configured SSH node displaying:
  - Node name, host, and username
  - Connection status (active, error, or unknown)
  - Latency (if measured)
  - Quick stats (total commands executed, last seen time)
- **Delete action** — Each node card has a delete option to remove the node
- **Summary statistics** — Total nodes, active connections, and recent command count

## Activity Page

The Activity page is a command log viewer that shows every command executed through Shuttle.

### Features

- **Command history** — Full list of commands with node name, command text, exit code, stdout/stderr output, security level, and execution duration
- **Time filters** — Filter logs by time range (last hour, last 24 hours, last 7 days, custom range)
- **Search** — Full-text search across command text and output
- **Node filter** — Filter logs to a specific node
- **Export** — Export the filtered log data for external analysis
- **Console-style display** — stdout and stderr are displayed in a terminal-style format with proper formatting

Each log entry includes:

| Field           | Description                                         |
| --------------- | --------------------------------------------------- |
| Command         | The executed command text                           |
| Node            | Which node it ran on                                |
| Exit code       | Process exit code (0 = success)                     |
| stdout / stderr | Full command output                                 |
| Security level  | Which rule level matched (block/confirm/warn/allow) |
| Duration        | Execution time in milliseconds                      |
| Timestamp       | When the command was executed                       |
| Bypassed        | Whether a confirm rule was bypassed with a token    |

## Security Rules Page

The Security Rules page lets you manage command security rules through the UI.

### Global Rules

Global rules apply to all nodes. The default rules (seeded on first startup) appear here. You can:

- **Add** new global rules with a pattern, level, description, and priority
- **Edit** existing rules (change level, pattern, description, priority)
- **Enable/disable** rules with a toggle
- **Delete** rules

### Per-Node Rules

Select a specific node to view and manage its overrides:

- **Add** a node-specific rule that overrides a global rule with the same pattern
- **View** which global rules are overridden for this node

### Effective Rules Preview

The rules page shows an **effective rules** view that resolves inheritance — displaying the final set of rules that will actually be applied for a given node, accounting for both global rules and node-specific overrides.

## Settings Page

The Settings page provides configuration for pool parameters and data management.

### Connection Pool Configuration

Adjust pool settings that take effect on the next restart:

- **Max total connections** — Total SSH connections across all nodes (default: 50)
- **Max per-node connections** — Connections per individual node (default: 5)
- **Idle timeout** — Seconds before idle connections are evicted (default: 300)
- **Max lifetime** — Maximum connection age in seconds (default: 3600)

### Cleanup Policy

Configure automatic data retention:

- **Command log retention** — Days to keep command logs (default: 30)
- **Closed session retention** — Days to keep closed sessions (default: 7)

Cleanup runs automatically on every Shuttle startup.

### Data Import/Export

- **Export** — Download the current database contents (nodes, rules, settings) as a JSON file for backup or migration
- **Import** — Upload a previously exported JSON file to restore configuration

This is useful for migrating Shuttle between machines or backing up your configuration before an upgrade.
