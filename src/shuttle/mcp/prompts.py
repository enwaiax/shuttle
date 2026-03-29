"""MCP prompt registrations for Shuttle.

Provides ``register_prompts()`` which adds reusable prompt templates that
leverage Shuttle's runtime state to give AI assistants actionable context.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

from shuttle.core.session import SessionManager


def register_prompts(
    mcp: Any,
    session_mgr: SessionManager,
    pool: Any,
    db_session_ctx: Callable[..., AsyncIterator],
    node_repo_factory: Callable,
) -> None:
    """Register all Shuttle MCP prompts on the given FastMCP instance."""

    @mcp.prompt()
    async def shuttle_overview() -> str:
        """Get a complete overview of the current Shuttle environment.

        Returns live node status, active sessions, security rule summary,
        and connection pool state — everything an AI assistant needs to
        start working with this Shuttle instance.
        """
        from shuttle.db.repository import RuleRepo

        # Nodes
        async with db_session_ctx() as db_sess:
            repo = node_repo_factory(db_sess)
            nodes = await repo.list_all()

        node_lines = []
        for n in nodes:
            icon = {"active": "●", "inactive": "○", "error": "✗"}.get(n.status, "?")
            node_lines.append(
                f"  {icon} {n.name} — {n.host}:{n.port} (user={n.username}, "
                f"auth={n.auth_type}, tags={n.tags or []})"
            )
        nodes_section = (
            "\n".join(node_lines) if node_lines else "  (no nodes configured)"
        )

        # Sessions
        active = session_mgr.list_active()
        session_lines = []
        for s in active:
            session_lines.append(
                f"  • {s.node_id} — cwd={s.working_directory}, "
                f"bypassed_rules={len(s.bypass_patterns)}"
            )
        sessions_section = (
            "\n".join(session_lines) if session_lines else "  (no active sessions)"
        )

        # Security rules
        async with db_session_ctx() as db_sess:
            rule_repo = RuleRepo(db_sess)
            rules = await rule_repo.list_all()

        blocked = [r for r in rules if r.level == "BLOCK" and r.enabled]
        confirm = [r for r in rules if r.level == "CONFIRM" and r.enabled]
        warn = [r for r in rules if r.level == "WARN" and r.enabled]

        # Pool
        pool_nodes = list(pool._registry.keys())
        total_idle = sum(len(q) for q in pool._idle.values())
        total_active = sum(pool._active.values())

        return (
            "# Shuttle Environment Overview\n\n"
            f"## Nodes ({len(nodes)})\n{nodes_section}\n\n"
            f"## Active Sessions ({len(active)})\n{sessions_section}\n\n"
            f"## Security Rules ({len(rules)} total)\n"
            f"  BLOCK: {len(blocked)} rules — commands matching these are rejected\n"
            f"  CONFIRM: {len(confirm)} rules — require explicit confirmation token\n"
            f"  WARN: {len(warn)} rules — allowed but logged with warning\n\n"
            f"## Connection Pool\n"
            f"  Registered: {len(pool_nodes)} nodes\n"
            f"  Active connections: {total_active}\n"
            f"  Idle connections: {total_idle}\n\n"
            "## Available Tools\n"
            "  • ssh_run(command, node) — execute command on a node\n"
            "  • ssh_list_nodes() — list configured nodes\n"
            "  • ssh_upload(node, local_path, remote_path) — SFTP upload\n"
            "  • ssh_download(node, remote_path, local_path) — SFTP download\n"
            "  • ssh_add_node(...) — add a new SSH node\n\n"
            "Use `shuttle://security-rules` resource to see exact rule patterns "
            "before running commands that might be blocked."
        )

    @mcp.prompt()
    async def safe_command_check(command: str, node: str | None = None) -> str:
        """Check if a command is safe to run before executing it.

        Evaluates the command against all active security rules and returns
        a detailed assessment — which rules match, what security level applies,
        and whether confirmation will be needed.
        """
        from shuttle.db.repository import RuleRepo

        async with db_session_ctx() as db_sess:
            rule_repo = RuleRepo(db_sess)
            rules = await rule_repo.list_all(node_id=None)

        # If node specified, also get node-specific rules
        node_rules = []
        if node:
            async with db_session_ctx() as db_sess:
                repo = node_repo_factory(db_sess)
                node_obj = await repo.get_by_name(node)
            if node_obj:
                async with db_session_ctx() as db_sess:
                    rule_repo = RuleRepo(db_sess)
                    node_rules = await rule_repo.list_all(node_id=node_obj.id)

        all_rules = rules + node_rules
        enabled_rules = [r for r in all_rules if r.enabled]

        import re

        matching = []
        for r in enabled_rules:
            try:
                if re.search(r.pattern, command):
                    matching.append(r)
            except re.error:
                pass

        if not matching:
            return (
                f"## Command Safety Check\n\n"
                f"**Command**: `{command}`\n"
                f"**Node**: {node or '(auto-select)'}\n"
                f"**Result**: ✅ ALLOW — no security rules matched.\n\n"
                "You can proceed with `ssh_run(command=...)`."
            )

        lines = []
        highest_level = "ALLOW"
        level_order = {"BLOCK": 3, "CONFIRM": 2, "WARN": 1, "ALLOW": 0}
        for r in matching:
            lines.append(
                f"  • [{r.level}] pattern=`{r.pattern}` — {r.description or 'no description'}"
            )
            if level_order.get(r.level, 0) > level_order.get(highest_level, 0):
                highest_level = r.level

        icon = {"BLOCK": "⛔", "CONFIRM": "⚠️", "WARN": "⚡"}.get(highest_level, "✅")

        advice = {
            "BLOCK": "This command will be rejected. Rephrase or use an alternative approach.",
            "CONFIRM": (
                "This command requires confirmation. Call ssh_run() first to get a "
                "confirm_token, then call ssh_run() again with that token."
            ),
            "WARN": "This command is allowed but will be logged with a warning. Proceed if intended.",
        }.get(highest_level, "Proceed normally.")

        return (
            f"## Command Safety Check\n\n"
            f"**Command**: `{command}`\n"
            f"**Node**: {node or '(auto-select)'}\n"
            f"**Result**: {icon} {highest_level}\n\n"
            f"### Matched Rules ({len(matching)})\n"
            + "\n".join(lines)
            + f"\n\n### Recommendation\n{advice}"
        )

    @mcp.prompt()
    async def node_context(node: str) -> str:
        """Get full operational context for a specific node.

        Returns the node's configuration, its active session state (including
        current working directory), applicable security rules, and recent
        command history — ready for the AI to operate on this node.
        """
        from shuttle.db.repository import LogRepo, RuleRepo

        # Node info
        async with db_session_ctx() as db_sess:
            repo = node_repo_factory(db_sess)
            node_obj = await repo.get_by_name(node)

        if not node_obj:
            return f"Node **{node}** not found. Run `ssh_list_nodes()` to see available nodes."

        # Active session
        active = session_mgr.list_active()
        node_session = next((s for s in active if s.node_id == node), None)

        session_info = (
            f"  Session ID: {node_session.session_id}\n"
            f"  Working directory: {node_session.working_directory}\n"
            f"  Bypassed rules: {list(node_session.bypass_patterns) or 'none'}"
            if node_session
            else "  No active session (will be auto-created on first ssh_run)"
        )

        # Node-specific security rules
        async with db_session_ctx() as db_sess:
            rule_repo = RuleRepo(db_sess)
            all_rules = await rule_repo.list_all()
            node_rules = await rule_repo.list_all(node_id=node_obj.id)

        global_rules = [r for r in all_rules if r.node_id is None and r.enabled]
        specific_rules = [r for r in node_rules if r.enabled]

        rule_lines = []
        for r in (specific_rules + global_rules)[:15]:
            scope = "node-specific" if r.node_id else "global"
            rule_lines.append(f"  [{r.level}] `{r.pattern}` ({scope})")

        rules_section = "\n".join(rule_lines) if rule_lines else "  (no rules)"

        # Recent command logs
        async with db_session_ctx() as db_sess:
            log_repo = LogRepo(db_sess)
            logs = await log_repo.list_by_node(node_id=node_obj.id, limit=10)

        log_lines = []
        for log in logs:
            icon = "✅" if log.exit_code == 0 else "❌"
            cmd_short = log.command[:60] + ("..." if len(log.command) > 60 else "")
            duration = f"{log.duration_ms}ms" if log.duration_ms else "?"
            log_lines.append(
                f"  {icon} `{cmd_short}` (exit={log.exit_code}, {duration})"
            )

        logs_section = "\n".join(log_lines) if log_lines else "  (no recent commands)"

        # Pool state
        pool_idle = len(pool._idle.get(node, []))
        pool_active = pool._active.get(node, 0)

        return (
            f"# Node: {node}\n\n"
            f"## Connection\n"
            f"  Host: {node_obj.host}:{node_obj.port}\n"
            f"  User: {node_obj.username}\n"
            f"  Auth: {node_obj.auth_type}\n"
            f"  Status: {node_obj.status}\n"
            f"  Tags: {node_obj.tags or []}\n"
            f"  Pool: {pool_active} active, {pool_idle} idle connections\n\n"
            f"## Current Session\n{session_info}\n\n"
            f"## Security Rules (top {len(rule_lines)})\n{rules_section}\n\n"
            f"## Recent Commands (last {len(log_lines)})\n{logs_section}\n\n"
            f"Ready to operate. Use `ssh_run(command=..., node='{node}')` to execute."
        )
