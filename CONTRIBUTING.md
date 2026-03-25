# Contributing to Shuttle

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/enwaiax/shuttle.git
cd shuttle

# Install Python dependencies
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install

# Install frontend dependencies
cd web && npm install && cd ..
```

## Running Locally

```bash
# Backend (MCP + Web)
uv run shuttle serve

# Frontend (hot reload, in another terminal)
cd web && npm run dev
```

## Making Changes

1. Create a branch: `git checkout -b feat/your-feature`
1. Make your changes
1. Run checks:

```bash
# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Tests
uv run pytest

# Frontend type check
cd web && npx tsc --noEmit

# All pre-commit hooks
uv run pre-commit run --all-files
```

4. Commit with a descriptive message following [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add jump host support to node form
fix: connection pool not releasing idle connections
docs: update MCP setup guide for Cursor
```

5. Push and open a Pull Request

## Project Structure

```
src/shuttle/
├── cli.py              # Typer CLI commands
├── core/               # Connection pool, sessions, security, credentials
├── db/                 # SQLAlchemy models, repositories, migrations
├── mcp/                # MCP server and tool definitions
└── web/                # FastAPI routes, schemas, static files

web/                    # React frontend (Vite + Tailwind + Radix)
├── src/
│   ├── pages/          # Route pages
│   ├── components/     # Shared UI components
│   ├── hooks/          # React hooks
│   └── api/            # API client (TanStack Query)

tests/                  # pytest test suites
docs/                   # Documentation site (Zensical)
```

## Code Style

- **Python:** Ruff for linting and formatting (88 char line length)
- **TypeScript:** Prettier defaults via Vite
- **Commits:** Conventional Commits format
- **Branches:** `feat/`, `fix/`, `docs/`, `chore/` prefixes

## Reporting Bugs

Open an issue with:

- Shuttle version (`shuttle --version`)
- Python version
- OS and architecture
- Steps to reproduce
- Expected vs actual behavior

## Questions?

Open a [GitHub Discussion](https://github.com/enwaiax/shuttle/discussions) or [Issue](https://github.com/enwaiax/shuttle/issues).
