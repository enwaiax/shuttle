"""MCP tool registrations for the Shuttle SSH gateway.

Provides ``register_tools()`` which wires up seven tools on a FastMCP instance:
ssh_execute, ssh_list_nodes, ssh_session_start, ssh_session_end,
ssh_session_list, ssh_upload, ssh_download.
"""

from __future__ import annotations

import time
from typing import Any, AsyncIterator, Callable, Optional

from loguru import logger

from shuttle.core.security import CommandGuard, ConfirmTokenStore, SecurityLevel
from shuttle.core.session import SessionManager

# Truncation limits
MAX_OUTPUT_BYTES = 10 * 1024 * 1024  # 10 MB for caller output
MAX_DB_OUTPUT_BYTES = 64 * 1024      # 64 KB for DB storage


def _truncate(text: str, limit: int) -> str:
    """Truncate *text* to *limit* bytes (UTF-8), appending a marker if truncated."""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return text
    return encoded[:limit].decode("utf-8", errors="replace") + "\n... [truncated]"


# ---------------------------------------------------------------------------
# Core execution logic (extracted for testability)
# ---------------------------------------------------------------------------

async def _execute_command_logic(
    *,
    command: str,
    node: Optional[str],
    session_id: Optional[str],
    timeout: float,
    confirm_token: Optional[str],
    bypass_scope: Optional[str],
    pool: Any,
    guard: CommandGuard,
    token_store: ConfirmTokenStore,
    session_mgr: SessionManager,
    db_session_ctx: Callable[..., AsyncIterator],
    node_repo_factory: Callable,
) -> str:
    """Execute a command with security checks, node resolution, and DB logging.

    Parameters
    ----------
    command : str
        The shell command to run.
    node : str | None
        Named node to target. Resolved from session if omitted.
    session_id : str | None
        If provided, execute within this session context.
    timeout : float
        Command timeout in seconds.
    confirm_token : str | None
        One-time confirmation token for CONFIRM-level commands.
    bypass_scope : str | None
        If "session", add the matched rule pattern to the session's bypass list.
    pool : ConnectionPool
        SSH connection pool.
    guard : CommandGuard
        Security rule evaluator.
    token_store : ConfirmTokenStore
        Token store for confirmation flow.
    session_mgr : SessionManager
        Session manager for session-based execution.
    db_session_ctx : callable
        Async context manager factory yielding a DB session.
    node_repo_factory : callable
        Factory that accepts a DB session and returns a NodeRepo.

    Returns
    -------
    str
        Command output or a security/error message.
    """
    from shuttle.db.repository import LogRepo

    # ── 1. Resolve target node ──────────────────────────────────────
    resolved_node: Optional[str] = node
    session_obj = None

    if session_id:
        session_obj = session_mgr.get(session_id)
        if session_obj is None:
            return f"Error: session '{session_id}' not found or already closed."
        resolved_node = resolved_node or session_obj.node_id

    if resolved_node is None:
        # Auto-select: if exactly one node is registered, use it
        async with db_session_ctx() as db_sess:
            repo = node_repo_factory(db_sess)
            all_nodes = await repo.list_all()
        if len(all_nodes) == 1:
            resolved_node = all_nodes[0].name
        else:
            return (
                "Error: no node specified and cannot auto-select "
                f"(found {len(all_nodes)} nodes). "
                "Provide 'node' or 'session_id'."
            )

    # ── 2. Security check ───────────────────────────────────────────
    bypass_patterns = list(session_obj.bypass_patterns) if session_obj else []
    decision = guard.evaluate(command, resolved_node, bypass_patterns=bypass_patterns)

    if decision.level == SecurityLevel.BLOCK:
        return f"BLOCKED: {decision.message}"

    if decision.level == SecurityLevel.CONFIRM:
        if confirm_token is None:
            # Create a token and ask the caller to confirm
            token = token_store.create(command, resolved_node)
            msg = (
                f"Command requires confirmation.\n"
                f"Rule: {decision.matched_rule}\n"
                f"Reason: {decision.message}\n"
                f"To proceed, re-call ssh_execute with confirm_token=\"{token}\""
            )
            return msg

        # Validate the provided token
        if not token_store.validate(confirm_token, command, resolved_node):
            return "Error: invalid or expired confirmation token."

        # Token valid — optionally add bypass for this session
        if bypass_scope == "session" and session_obj and decision.matched_rule:
            # The matched_rule here is the rule *name*; we need the pattern string.
            # CommandGuard stores matched_rule as the rule name, but bypass_patterns
            # are checked against pattern_str. We'll search for the matching pattern.
            for rule in guard._rules:
                if rule.name == decision.matched_rule:
                    session_obj.bypass_patterns.add(rule.pattern_str)
                    break

    if decision.level == SecurityLevel.WARN:
        logger.warning(
            "WARN rule matched: rule={rule} command={cmd} node={node}",
            rule=decision.matched_rule,
            cmd=command,
            node=resolved_node,
        )

    # ── 3. Execute ──────────────────────────────────────────────────
    start_ts = time.monotonic()

    if session_obj is not None:
        # Session-based execution (handles DB logging internally)
        result = await session_mgr.execute(session_id, command, timeout=timeout)
        stdout = result["stdout"]
    else:
        # Stateless execution via pool
        try:
            async with pool.connection(resolved_node) as pc:
                ssh_result = await pc.conn.run(command, timeout=timeout, check=False)
                stdout = ssh_result.stdout or ""
                exit_code = ssh_result.exit_code
        except Exception as exc:
            return f"Error: command execution failed — {exc}"

        # Truncate output for caller
        stdout = _truncate(stdout, MAX_OUTPUT_BYTES)

        # Log to DB (stateless, session_id=None)
        elapsed_ms = int((time.monotonic() - start_ts) * 1000)
        db_stdout = _truncate(stdout, MAX_DB_OUTPUT_BYTES)
        try:
            async with db_session_ctx() as db_sess:
                log_repo = LogRepo(db_sess)
                await log_repo.create(
                    node_id=resolved_node,
                    command=command,
                    session_id=None,
                    exit_code=exit_code,
                    stdout=db_stdout,
                    security_level=decision.level.value,
                    security_rule_id=None,
                    bypassed=bool(confirm_token),
                    duration_ms=elapsed_ms,
                )
        except Exception:
            logger.exception("Failed to persist command log")

    return stdout


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_tools(
    mcp: Any,
    pool: Any,
    guard: CommandGuard,
    token_store: ConfirmTokenStore,
    session_mgr: SessionManager,
    db_session_ctx: Callable,
    node_repo_factory: Callable,
) -> None:
    """Register all Shuttle MCP tools on the given FastMCP instance.

    Parameters
    ----------
    mcp : FastMCP
        The FastMCP server to register tools on.
    pool : ConnectionPool
        SSH connection pool.
    guard : CommandGuard
        Security evaluator.
    token_store : ConfirmTokenStore
        Confirmation token store.
    session_mgr : SessionManager
        Session manager.
    db_session_ctx : callable
        Async context manager factory yielding a DB AsyncSession.
    node_repo_factory : callable
        Factory accepting a DB session and returning a NodeRepo.
    """

    # ── ssh_execute ─────────────────────────────────────────────────
    @mcp.tool()
    async def ssh_execute(
        command: str,
        node: Optional[str] = None,
        session_id: Optional[str] = None,
        timeout: float = 30.0,
        confirm_token: Optional[str] = None,
        bypass_scope: Optional[str] = None,
    ) -> str:
        """Execute a shell command on a remote SSH node.

        Supports session-based (stateful) and stateless execution with
        security checks (BLOCK / CONFIRM / WARN / ALLOW).
        """
        return await _execute_command_logic(
            command=command,
            node=node,
            session_id=session_id,
            timeout=timeout,
            confirm_token=confirm_token,
            bypass_scope=bypass_scope,
            pool=pool,
            guard=guard,
            token_store=token_store,
            session_mgr=session_mgr,
            db_session_ctx=db_session_ctx,
            node_repo_factory=node_repo_factory,
        )

    # ── ssh_list_nodes ──────────────────────────────────────────────
    @mcp.tool()
    async def ssh_list_nodes() -> str:
        """List all configured SSH nodes with status icons."""
        async with db_session_ctx() as db_sess:
            repo = node_repo_factory(db_sess)
            nodes = await repo.list_all()

        if not nodes:
            return "No nodes configured."

        lines = []
        for n in nodes:
            icon = {"active": "[OK]", "inactive": "[--]", "error": "[!!]"}.get(
                n.status, "[??]"
            )
            lines.append(f"{icon} {n.name}  ({n.host}:{n.port}, user={n.username})")
        return "\n".join(lines)

    # ── ssh_session_start ───────────────────────────────────────────
    @mcp.tool()
    async def ssh_session_start(node: str) -> str:
        """Start a new SSH session on the named node."""
        try:
            session = await session_mgr.create(node)
        except Exception as exc:
            return f"Error: failed to start session — {exc}"
        return (
            f"Session started.\n"
            f"  session_id: {session.session_id}\n"
            f"  node: {session.node_id}\n"
            f"  cwd: {session.working_directory}"
        )

    # ── ssh_session_end ─────────────────────────────────────────────
    @mcp.tool()
    async def ssh_session_end(session_id: str) -> str:
        """Close an active SSH session."""
        session = session_mgr.get(session_id)
        if session is None:
            return f"Error: session '{session_id}' not found or already closed."
        await session_mgr.close(session_id)
        return f"Session '{session_id}' closed."

    # ── ssh_session_list ────────────────────────────────────────────
    @mcp.tool()
    async def ssh_session_list() -> str:
        """List all active SSH sessions."""
        sessions = session_mgr.list_active()
        if not sessions:
            return "No active sessions."
        lines = []
        for s in sessions:
            lines.append(
                f"  {s.session_id}  node={s.node_id}  cwd={s.working_directory}"
            )
        return "\n".join(lines)

    # ── ssh_upload ──────────────────────────────────────────────────
    @mcp.tool()
    async def ssh_upload(
        node: str,
        local_path: str,
        remote_path: str,
    ) -> str:
        """Upload a file to a remote node via SFTP."""
        try:
            async with pool.connection(node) as pc:
                async with pc.conn.start_sftp_client() as sftp:
                    await sftp.put(local_path, remote_path)
            return f"Uploaded {local_path} -> {node}:{remote_path}"
        except Exception as exc:
            return f"Error: upload failed — {exc}"

    # ── ssh_download ────────────────────────────────────────────────
    @mcp.tool()
    async def ssh_download(
        node: str,
        remote_path: str,
        local_path: str,
    ) -> str:
        """Download a file from a remote node via SFTP."""
        try:
            async with pool.connection(node) as pc:
                async with pc.conn.start_sftp_client() as sftp:
                    await sftp.get(remote_path, local_path)
            return f"Downloaded {node}:{remote_path} -> {local_path}"
        except Exception as exc:
            return f"Error: download failed — {exc}"
