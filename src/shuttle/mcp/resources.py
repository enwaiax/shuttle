"""MCP resource registrations for Shuttle.

Provides ``register_resources()`` which exposes Shuttle's live runtime state
as MCP resources — nodes, security rules, sessions, command history, and
connection pool status.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from shuttle.core.session import SessionManager


def register_resources(
    mcp: Any,
    pool: Any,
    session_mgr: SessionManager,
    db_session_ctx: Callable[..., AsyncIterator],
    node_repo_factory: Callable,
) -> None:
    """Register all Shuttle MCP resources on the given FastMCP instance."""

    @mcp.resource("shuttle://nodes")
    async def list_nodes() -> str:
        """All configured SSH nodes with connection details and status."""
        async with db_session_ctx() as db_sess:
            repo = node_repo_factory(db_sess)
            nodes = await repo.list_all()

        items = []
        for n in nodes:
            items.append(
                {
                    "name": n.name,
                    "host": n.host,
                    "port": n.port,
                    "username": n.username,
                    "status": n.status,
                    "auth_type": n.auth_type,
                    "tags": n.tags or [],
                    "last_seen_at": n.last_seen_at.isoformat()
                    if n.last_seen_at
                    else None,
                }
            )
        return json.dumps({"nodes": items, "total": len(items)})

    @mcp.resource("shuttle://nodes/{name}")
    async def get_node_detail(name: str) -> str:
        """Detailed information for a specific SSH node including pool state."""
        async with db_session_ctx() as db_sess:
            repo = node_repo_factory(db_sess)
            node = await repo.get_by_name(name)

        if not node:
            return json.dumps({"error": f"Node '{name}' not found"})

        return json.dumps(
            {
                "name": node.name,
                "host": node.host,
                "port": node.port,
                "username": node.username,
                "status": node.status,
                "auth_type": node.auth_type,
                "tags": node.tags or [],
                "pool": {
                    "active_connections": pool._active.get(name, 0),
                    "idle_connections": len(pool._idle.get(name, [])),
                    "registered": name in pool._registry,
                },
                "last_seen_at": node.last_seen_at.isoformat()
                if node.last_seen_at
                else None,
                "created_at": node.created_at.isoformat() if node.created_at else None,
                "updated_at": node.updated_at.isoformat() if node.updated_at else None,
            }
        )

    @mcp.resource("shuttle://security-rules")
    async def list_security_rules() -> str:
        """All security rules governing command execution, grouped by level."""
        from shuttle.db.repository import RuleRepo

        async with db_session_ctx() as db_sess:
            rule_repo = RuleRepo(db_sess)
            rules = await rule_repo.list_all()

        items = []
        for r in rules:
            items.append(
                {
                    "id": r.id,
                    "pattern": r.pattern,
                    "level": r.level,
                    "description": r.description,
                    "priority": r.priority,
                    "enabled": r.enabled,
                    "node_id": r.node_id,
                }
            )

        by_level = {}
        for r in items:
            by_level.setdefault(r["level"], []).append(r)

        return json.dumps(
            {
                "rules": items,
                "total": len(items),
                "by_level": {k: len(v) for k, v in by_level.items()},
            }
        )

    @mcp.resource("shuttle://sessions")
    async def list_active_sessions() -> str:
        """Currently active SSH sessions with working directory and bypass state."""
        active = session_mgr.list_active()

        items = []
        for s in active:
            items.append(
                {
                    "session_id": s.session_id,
                    "node_id": s.node_id,
                    "working_directory": s.working_directory,
                    "bypass_patterns": list(s.bypass_patterns),
                    "env_vars": s.env_vars,
                }
            )
        return json.dumps({"sessions": items, "total": len(items)})

    @mcp.resource("shuttle://pool-status")
    async def get_pool_status() -> str:
        """Connection pool health — per-node active/idle counts and config."""
        per_node = {}
        for node_id in pool._registry:
            per_node[node_id] = {
                "active": pool._active.get(node_id, 0),
                "idle": len(pool._idle.get(node_id, [])),
            }

        return json.dumps(
            {
                "config": {
                    "max_per_node": pool._config.max_per_node,
                    "max_total": pool._config.max_total,
                    "idle_timeout_s": pool._config.idle_timeout,
                    "max_lifetime_s": pool._config.max_lifetime,
                },
                "global_active": pool._global_active,
                "registered_nodes": len(pool._registry),
                "per_node": per_node,
            }
        )

    @mcp.resource("shuttle://logs/{node_name}/recent")
    async def get_recent_logs(node_name: str) -> str:
        """Recent command execution history for a node (last 20 commands)."""
        from shuttle.db.repository import LogRepo

        async with db_session_ctx() as db_sess:
            repo = node_repo_factory(db_sess)
            node_obj = await repo.get_by_name(node_name)

        if not node_obj:
            return json.dumps({"error": f"Node '{node_name}' not found"})

        async with db_session_ctx() as db_sess:
            log_repo = LogRepo(db_sess)
            logs = await log_repo.list_by_node(node_id=node_obj.id, limit=20)

        items = []
        for log in logs:
            items.append(
                {
                    "command": log.command,
                    "exit_code": log.exit_code,
                    "security_level": log.security_level,
                    "bypassed": log.bypassed,
                    "duration_ms": log.duration_ms,
                    "executed_at": log.executed_at.isoformat()
                    if log.executed_at
                    else None,
                }
            )

        return json.dumps(
            {
                "node": node_name,
                "logs": items,
                "total": len(items),
            }
        )
