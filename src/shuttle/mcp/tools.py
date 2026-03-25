"""MCP tool registrations for the Shuttle SSH gateway.

Provides ``register_tools()`` which wires up five tools on a FastMCP instance:
ssh_run, ssh_list_nodes, ssh_upload, ssh_download, ssh_add_node.

Sessions are managed implicitly: ``ssh_run`` auto-creates or reuses a session
per node so that working directory context is preserved across calls.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

from loguru import logger

from shuttle.core.security import CommandGuard, ConfirmTokenStore, SecurityLevel
from shuttle.core.session import SessionManager

# Truncation limits
MAX_OUTPUT_BYTES = 10 * 1024 * 1024  # 10 MB for caller output
MAX_DB_OUTPUT_BYTES = 64 * 1024  # 64 KB for DB storage


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
    node: str | None,
    timeout: float,
    confirm_token: str | None,
    bypass_scope: str | None,
    pool: Any,
    guard: CommandGuard,
    token_store: ConfirmTokenStore,
    session_mgr: SessionManager,
    db_session_ctx: Callable[..., AsyncIterator],
    node_repo_factory: Callable,
) -> str:
    """Execute a command with security checks, node resolution, and DB logging.

    Sessions are implicit: if an active session exists for the resolved node it
    is reused; otherwise a new session is created automatically.

    Parameters
    ----------
    command : str
        The shell command to run.
    node : str | None
        Named node to target.  Auto-selected when only one node exists.
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
    # -- 1. Resolve target node -----------------------------------------------
    resolved_node: str | None = node

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
                "Provide 'node'."
            )

    # -- 2. Auto-session: find existing or create ----------------------------
    active_sessions = session_mgr.list_active()
    node_session = next(
        (s for s in active_sessions if s.node_id == resolved_node), None
    )
    if node_session:
        session_id = node_session.session_id
        session_obj = node_session
    else:
        try:
            new_session = await session_mgr.create(resolved_node)
            session_id = new_session.session_id
            session_obj = new_session
        except Exception as exc:
            return f"Error: failed to auto-create session — {exc}"

    # -- 3. Security check ----------------------------------------------------
    bypass_patterns = list(session_obj.bypass_patterns) if session_obj else []
    async with db_session_ctx() as db_sess:
        decision = await guard.evaluate(
            command, resolved_node, db_sess, bypass_patterns
        )

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
                f'To proceed, re-call ssh_run with confirm_token="{token}"'
            )
            return msg

        # Validate the provided token
        if not token_store.validate(confirm_token, command, resolved_node):
            return "Error: invalid or expired confirmation token."

        # Token valid — optionally add bypass for this session
        if bypass_scope == "session" and session_obj and decision.matched_rule:
            async with db_session_ctx() as db_sess:
                from shuttle.db.repository import RuleRepo

                rule_repo = RuleRepo(db_sess)
                matched = await rule_repo.get_by_id(decision.matched_rule)
                if matched:
                    session_obj.bypass_patterns.add(matched.pattern)

    if decision.level == SecurityLevel.WARN:
        logger.warning(
            "WARN rule matched: rule={rule} command={cmd} node={node}",
            rule=decision.matched_rule,
            cmd=command,
            node=resolved_node,
        )

    # -- 4. Execute via session -----------------------------------------------
    result = await session_mgr.execute(session_id, command, timeout=timeout)
    stdout = result["stdout"]

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
    cred_mgr: Any = None,
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
    cred_mgr : CredentialManager | None
        Credential manager for encrypting node credentials.
    """

    # -- ssh_run --------------------------------------------------------------
    @mcp.tool()
    async def ssh_run(
        command: str,
        node: str | None = None,
        timeout: float = 30.0,
        confirm_token: str | None = None,
        bypass_scope: str | None = None,
    ) -> str:
        """Execute a shell command on a remote SSH node.

        Sessions are managed automatically: working directory is preserved
        across calls to the same node. Security checks (BLOCK / CONFIRM /
        WARN / ALLOW) are applied before execution.
        """
        return await _execute_command_logic(
            command=command,
            node=node,
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

    # -- ssh_list_nodes -------------------------------------------------------
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

    # -- ssh_upload -----------------------------------------------------------
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

    # -- ssh_download ---------------------------------------------------------
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

    # -- ssh_add_node ---------------------------------------------------------
    @mcp.tool()
    async def ssh_add_node(
        name: str,
        host: str,
        port: int = 22,
        username: str = "",
        password: str | None = None,
        private_key: str | None = None,
        jump_host: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Add a new SSH node to the Shuttle configuration."""
        from shuttle.core.proxy import NodeConnectInfo

        # Validate credentials
        if password is None and private_key is None:
            return "Error: either 'password' or 'private_key' must be provided."

        if cred_mgr is None:
            return (
                "Error: credential manager not available — cannot encrypt credentials."
            )

        # Determine auth type and encrypt credential
        if private_key is not None:
            auth_type = "key"
            encrypted = cred_mgr.encrypt(private_key)
        else:
            auth_type = "password"
            encrypted = cred_mgr.encrypt(password)

        # Resolve jump_host name to UUID if provided
        jump_host_id: str | None = None
        if jump_host is not None:
            async with db_session_ctx() as db_sess:
                repo = node_repo_factory(db_sess)
                jh = await repo.get_by_name(jump_host)
            if jh is None:
                return f"Error: jump host '{jump_host}' not found."
            jump_host_id = jh.id

        # Check for duplicate name
        async with db_session_ctx() as db_sess:
            repo = node_repo_factory(db_sess)
            existing = await repo.get_by_name(name)
        if existing is not None:
            return f"Error: node '{name}' already exists."

        # Create node in DB
        async with db_session_ctx() as db_sess:
            repo = node_repo_factory(db_sess)
            node_obj = await repo.create(
                name=name,
                host=host,
                port=port,
                username=username,
                auth_type=auth_type,
                encrypted_credential=encrypted,
                jump_host_id=jump_host_id,
                tags=tags,
            )

        # Resolve jump host connection info if present
        jump_host_info: NodeConnectInfo | None = None
        if jump_host_id is not None:
            async with db_session_ctx() as db_sess:
                repo = node_repo_factory(db_sess)
                jh_node = await repo.get_by_id(jump_host_id)
            if jh_node is not None and jh_node.encrypted_credential and cred_mgr:
                jh_decrypted = cred_mgr.decrypt(jh_node.encrypted_credential)
                jump_host_info = NodeConnectInfo(
                    node_id=jh_node.name,
                    hostname=jh_node.host,
                    port=jh_node.port,
                    username=jh_node.username,
                    password=jh_decrypted if jh_node.auth_type == "password" else None,
                    private_key=jh_decrypted if jh_node.auth_type == "key" else None,
                )

        # Register in connection pool
        info = NodeConnectInfo(
            node_id=name,
            hostname=host,
            port=port,
            username=username,
            password=password if auth_type == "password" else None,
            private_key=private_key if auth_type == "key" else None,
            jump_host=jump_host_info,
        )
        pool.register_node(info)

        return f"Node '{name}' added (id={node_obj.id})."
