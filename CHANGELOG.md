# Changelog

All notable changes to Shuttle are documented here.

## [0.2.1] - 2026-03-21

### Changed
- Switch license from ISC to MIT
- Add pre-commit hooks (ruff, trailing-whitespace, uv-lock)
- Upgrade ruff rules (isort, pyupgrade, bugbear, comprehensions)
- Auto-fix 73 lint issues across codebase
- CLI: Rich table output for `node list` and `config show`
- CLI: `node add` supports non-interactive mode (`--name`, `--host`, etc.)
- CLI: Input validation — empty fields rejected, key file existence checked
- Node default status changed from `active` to `inactive` until test passes
- Replace mkdocs.yml with zensical.toml
- Fix CI Node.js 20 deprecation (upgrade to Node 22)
- Fix Codecov upload configuration

## [0.2.0] - 2026-03-21

### Added
- **Service mode** (`shuttle serve`) — MCP + Web UI on a single HTTP port
- **Web control panel** — React dark-theme UI with nodes, activity logs, rules, settings
- **9 MCP tools** — ssh_execute, ssh_upload, ssh_download, ssh_list_nodes, ssh_add_node, ssh_remove_node, ssh_session_start/end/list
- **4-level command security** — block, confirm, warn, allow with regex patterns
- **Connection pooling** — per-node SSH connection reuse with idle eviction
- **Session isolation** — stateful sessions with working directory tracking
- **Per-node security rules** — override global defaults per server
- **Jump host support** — connect through bastion servers
- **Credential encryption** — Fernet encryption for passwords and private keys at rest
- **18 REST API endpoints** — nodes, rules, sessions, logs, settings, stats
- **Auto-cleanup** — old logs and closed sessions cleaned up on startup
- **Database indexes** — optimized query performance for hot paths

### Infrastructure
- SQLAlchemy 2.0 async ORM with SQLite WAL mode
- FastMCP 2.0 with Context dependency injection
- Typer CLI with interactive and non-interactive modes
- GitHub Actions CI (test + frontend + build), docs deploy, release pipeline
- Codecov integration

## [0.1.0] - 2025-12-01

### Added
- Initial release — basic SSH MCP tools (execute, upload, download)
- FastMCP server with stdio transport
- Simple command whitelist/blacklist security
