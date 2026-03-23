<div align="center">

# 🚀 Shuttle

**Secure SSH gateway for AI assistants**

[![CI](https://img.shields.io/github/actions/workflow/status/enwaiax/shuttle/test.yml?style=flat-square&label=CI)](https://github.com/enwaiax/shuttle/actions/workflows/test.yml)
[![codecov](https://img.shields.io/codecov/c/github/enwaiax/shuttle?style=flat-square&color=76B900)](https://codecov.io/gh/enwaiax/shuttle)
[![PyPI](https://img.shields.io/pypi/v/shuttle-mcp?style=flat-square&color=76B900)](https://pypi.org/project/shuttle-mcp)
[![Downloads](https://img.shields.io/pepy/dt/shuttle-mcp?style=flat-square&color=76B900&label=downloads)](https://pepy.tech/project/shuttle-mcp)
[![Python](https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Docs](https://img.shields.io/badge/docs-enwaiax.github.io%2Fshuttle-76B900?style=flat-square)](https://enwaiax.github.io/shuttle/)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

Shuttle lets AI assistants (Claude Code, Cursor, etc.) securely execute commands on your remote SSH servers — with connection pooling, session isolation, command safety rules, and a web audit panel.

[Getting Started](#getting-started) · [MCP Tools](#mcp-tools) · [Web Panel](#web-panel) · [Security Rules](#security-rules) · [Docs](https://enwaiax.github.io/shuttle/) · [中文文档](README_CN.md)

</div>

---

## Why Shuttle?

When AI coding assistants need to operate remote servers (run tests on GPU machines, deploy to staging, check logs), they need a secure bridge. Shuttle provides:

- **🔐 4-Level Command Security** — Block dangerous commands, require confirmation for risky ones, warn on installs, allow the rest
- **🔄 Connection Pooling** — Reuse SSH connections across commands, no repeated handshakes
- **📦 Session Isolation** — Each AI conversation gets its own working directory context
- **🌐 Web Audit Panel** — See every command the AI ran, per node, with full stdout/stderr
- **🛡️ Per-Node Rules** — Different security policies for prod vs dev servers
- **⚡ Jump Host Support** — Connect through bastion/jump servers

## Getting Started

### 1. Install

```bash
# Recommended: install CLI once (tools bin on PATH)
uv tool install shuttle-mcp
shuttle --help

# Or run without installing (stdio / one-off)
uvx shuttle-mcp --help

# Older PyPI wheels without the `shuttle-mcp` script:
# uvx --from shuttle-mcp shuttle --help
```

### 2. Add your first node

```bash
shuttle node add
# Follow the prompts: name, host, username, password/key
```

### 3. Connect to your AI assistant

**Claude Code / Cursor (stdio mode):**

```json
// .mcp.json
{
  "mcpServers": {
    "shuttle": {
      "command": "uvx",
      "args": ["shuttle-mcp"]
    }
  }
}
```

**Service mode (with Web UI):**

```bash
# Start the service
shuttle serve

# Then configure your AI client with the URL
```

```json
// .mcp.json
{
  "mcpServers": {
    "shuttle": {
      "url": "http://localhost:9876/mcp/"
    }
  }
}
```

That's it. Your AI assistant can now execute commands on your remote servers.

## Two Running Modes

| Mode | Command | MCP Transport | Web UI | Use Case |
|------|---------|--------------|--------|----------|
| **CLI** | `shuttle` | stdio | ❌ | Quick use, AI client manages lifecycle |
| **Service** | `shuttle serve` | streamable-http | ✅ http://localhost:9876 | Audit logs, manage rules, cloud deploy |

Both modes share the same SQLite database — commands logged in CLI mode are visible in the Web UI when you switch to service mode.

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

### Example conversation

```
You: Check the GPU usage on my training server
AI:  → ssh_execute(node="gpu-server", command="nvidia-smi")
AI:  Your GPU server has 7x A100-80GB, all idle at 0% utilization.

You: Start a training run
AI:  → ssh_session_start(node="gpu-server")
AI:  → ssh_execute(session_id="abc123", command="cd /workspace && python train.py")
AI:  Training started. Epoch 1/10...
```

## Security Rules

Commands are evaluated against a 4-level security system:

| Level | Behavior | Example |
|-------|----------|---------|
| 🔴 **block** | Rejected immediately | `rm -rf /`, `mkfs`, fork bomb |
| 🟡 **confirm** | Requires user confirmation | `sudo`, `rm -rf`, `shutdown` |
| 🟠 **warn** | Executes with warning logged | `apt install`, `pip install` |
| 🟢 **allow** | Executes normally | Everything else |

Default rules are seeded on first startup. Customize via Web UI or directly in the database.

### Per-Node Overrides

Different servers can have different rules:

```
Global: sudo .* → confirm
GPU Server: sudo .* → allow (trusted environment)
Prod Server: DROP TABLE → block (extra protection)
```

## Web Panel

Start with `shuttle serve`, open `http://localhost:9876`:

- **Overview** — Node cards with status, quick stats
- **Activity** — Per-node command log (console-style, with stdout/stderr)
- **Security Rules** — Manage global defaults and per-node overrides
- **Settings** — Connection pool and cleanup configuration

The Web UI requires a bearer token (displayed when you run `shuttle serve`).

## CLI Reference

```bash
# MCP Server
shuttle                      # Start MCP server (stdio mode)
shuttle serve                # Start service mode (MCP + Web)
shuttle serve --port 8080    # Custom port
shuttle serve --host 0.0.0.0 # Bind to all interfaces

# Node Management
shuttle node add             # Add node interactively
shuttle node list            # List all nodes
shuttle node test <name>     # Test SSH connection
shuttle node edit <name>     # Edit a node
shuttle node remove <name>   # Remove a node

# Configuration
shuttle config show          # Display current config
```

## Configuration

All settings can be overridden with environment variables (prefix `SHUTTLE_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SHUTTLE_DB_URL` | `sqlite+aiosqlite:///~/.shuttle/shuttle.db` | Database URL |
| `SHUTTLE_WEB_PORT` | `9876` | Web panel port |
| `SHUTTLE_POOL_MAX_TOTAL` | `50` | Max total SSH connections |
| `SHUTTLE_POOL_MAX_PER_NODE` | `5` | Max connections per node |
| `SHUTTLE_POOL_IDLE_TIMEOUT` | `300` | Idle connection timeout (seconds) |

### Using PostgreSQL

```bash
SHUTTLE_DB_URL=postgresql+asyncpg://user:pass@host:5432/shuttle shuttle serve
```

Requires: `uv pip install asyncpg` (install into the same environment that runs Shuttle)

## Development

```bash
# Clone and install
git clone https://github.com/enwaiax/shuttle.git
cd shuttle
uv sync

# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/

# Frontend dev (hot reload)
cd web && npm install && npm run dev
# Backend: uv run shuttle serve (in another terminal)
```

## Architecture

```
Developer ↔ AI Assistant ↔ Shuttle (MCP) ↔ SSH ↔ Remote Servers
                              │
                    ┌─────────┴──────────┐
                    │   Core Engine       │
                    │  ├ ConnectionPool   │
                    │  ├ SessionManager   │
                    │  ├ CommandGuard     │
                    │  └ SQLAlchemy ORM   │
                    └────────────────────┘
```

**Service mode:** Single ASGI app serving both MCP (at `/mcp/`) and Web UI (at `/`) on the same port.

## License

[MIT](LICENSE)

---

<div align="center">
  <sub>Built for developers who let AI do the SSH-ing.</sub>
</div>
