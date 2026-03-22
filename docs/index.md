# Shuttle

**Secure SSH gateway for AI assistants**

Shuttle lets AI assistants (Claude Code, Cursor, etc.) securely execute commands on your remote SSH servers --- with connection pooling, session isolation, command safety rules, and a web audit panel.

## Features

- **4-Level Command Security** --- Block dangerous commands, require confirmation for risky ones, warn on installs, allow the rest
- **Connection Pooling** --- Reuse SSH connections across commands, no repeated handshakes
- **Session Isolation** --- Each AI conversation gets its own working directory context
- **Web Audit Panel** --- See every command the AI ran, per node, with full stdout/stderr
- **Per-Node Rules** --- Different security policies for prod vs dev servers
- **Jump Host Support** --- Connect through bastion/jump servers

## Quick Start

### 1. Install

```bash
# Via uvx (recommended)
uvx shuttle-mcp

# Or pip
pip install shuttle-mcp
```

### 2. Add your first node

```bash
shuttle node add
# Follow the prompts: name, host, username, password/key
```

### 3. Connect to your AI assistant

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

See [MCP Setup](mcp-setup.md) for detailed instructions for Claude Code, Cursor, and both transport modes.

## MCP Tools

AI assistants get these tools automatically:

| Tool | Description |
|------|-------------|
| `ssh_execute` | Run a command on a remote node |
| `ssh_upload` | Upload a file via SFTP |
| `ssh_download` | Download a file via SFTP |
| `ssh_list_nodes` | List all configured nodes |
| `ssh_add_node` | Add a new SSH node |
| `ssh_remove_node` | Remove a node |
| `ssh_session_start` | Start a stateful session (preserves working directory) |
| `ssh_session_end` | End a session |
| `ssh_session_list` | List active sessions |

## Architecture

```
Developer <-> AI Assistant <-> Shuttle (MCP) <-> SSH <-> Remote Servers
                                  |
                        +--------------------+
                        |   Core Engine      |
                        |  - ConnectionPool  |
                        |  - SessionManager  |
                        |  - CommandGuard    |
                        |  - SQLAlchemy ORM  |
                        +--------------------+
```

**Service mode** runs a single ASGI app serving both MCP (at `/mcp/`) and the Web UI (at `/`) on the same port.

## Documentation

- [Configuration](configuration.md) --- Environment variables, database URLs, pool parameters
- [Security Rules](security-rules.md) --- 4-level rule system, regex patterns, per-node overrides
- [MCP Setup](mcp-setup.md) --- Claude Code, Cursor, stdio and HTTP modes
- [Web Panel](web-panel.md) --- Overview, activity logs, rule management, settings

## License

[MIT](https://github.com/enwaiax/shuttle/blob/main/LICENSE)
