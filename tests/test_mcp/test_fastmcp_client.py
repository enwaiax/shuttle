"""FastMCP in-memory client tests for Shuttle MCP tools.

Uses ``fastmcp.Client(server)`` to exercise tools end-to-end without SSH or
network, validating tool registration, argument schemas, security flow, and
DB logging through the real FastMCP protocol layer.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastmcp import Client, FastMCP
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from shuttle.core.security import CommandGuard, ConfirmTokenStore
from shuttle.core.session import SSHSession
from shuttle.db.models import Base, CommandLog
from shuttle.db.repository import NodeRepo, RuleRepo
from shuttle.mcp.tools import register_tools

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result_text(result) -> str:
    """Extract text from a FastMCP CallToolResult."""
    if hasattr(result, "content") and result.content:
        return result.content[0].text
    if hasattr(result, "data") and result.data is not None:
        return str(result.data)
    return str(result)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_pool():
    p = MagicMock()
    p._registry = {}
    p.start_eviction_loop = AsyncMock()
    p.register_node = MagicMock()
    return p


@pytest.fixture
def mock_session_mgr():
    from shuttle.core.session import SessionManager

    mgr = MagicMock(spec=SessionManager)
    mgr.list_active.return_value = []
    return mgr


@pytest_asyncio.fixture
async def db_engine(tmp_path):
    db_path = tmp_path / "fastmcp_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_factory(db_engine):
    return sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def mcp_server(mock_pool, mock_session_mgr, db_factory):
    """Build a FastMCP server with real DB but mocked SSH."""
    mcp = FastMCP(name="shuttle-test")
    guard = CommandGuard()
    token_store = ConfirmTokenStore()

    @asynccontextmanager
    async def db_session_ctx():
        async with db_factory() as sess:
            yield sess

    async with db_factory() as sess:
        node_repo = NodeRepo(sess)
        await node_repo.create(
            name="test-node",
            host="10.0.0.1",
            port=22,
            username="root",
            auth_type="password",
            encrypted_credential="enc",
        )

    register_tools(
        mcp=mcp,
        pool=mock_pool,
        guard=guard,
        token_store=token_store,
        session_mgr=mock_session_mgr,
        db_session_ctx=db_session_ctx,
        node_repo_factory=NodeRepo,
    )
    return mcp


@pytest_asyncio.fixture
async def mcp_server_with_session(mcp_server, mock_session_mgr):
    """mcp_server + session_mgr pre-configured to simulate execution."""
    session = SSHSession(session_id="test-sess-1", node_id="test-node")
    mock_session_mgr.list_active.return_value = [session]
    mock_session_mgr.create = AsyncMock(return_value=session)
    mock_session_mgr.execute = AsyncMock(
        return_value={
            "stdout": "mocked output",
            "exit_status": 0,
            "working_directory": "/home/root",
        }
    )
    return mcp_server


# ---------------------------------------------------------------------------
# Tool registration / discovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_discovers_all_tools(mcp_server):
    """FastMCP Client.list_tools() must see all 5 Shuttle tools."""
    async with Client(mcp_server) as client:
        tools = await client.list_tools()

    tool_names = {t.name for t in tools}
    expected = {
        "ssh_run",
        "ssh_list_nodes",
        "ssh_upload",
        "ssh_download",
        "ssh_add_node",
    }
    assert expected == tool_names


@pytest.mark.asyncio
async def test_tool_schemas_have_descriptions(mcp_server):
    """Every tool must have a non-empty description."""
    async with Client(mcp_server) as client:
        tools = await client.list_tools()

    for tool in tools:
        assert tool.description, f"Tool {tool.name} has no description"


# ---------------------------------------------------------------------------
# ssh_list_nodes via Client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_nodes_via_client(mcp_server):
    """ssh_list_nodes called through Client returns the seeded node."""
    async with Client(mcp_server) as client:
        result = await client.call_tool("ssh_list_nodes", {})

    text = _result_text(result)
    assert "test-node" in text
    assert "10.0.0.1" in text


# ---------------------------------------------------------------------------
# ssh_run via Client — security flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_allowed_command_via_client(mcp_server_with_session):
    """ALLOW-level command executes and returns output through Client."""
    async with Client(mcp_server_with_session) as client:
        result = await client.call_tool(
            "ssh_run", {"command": "hostname", "node": "test-node"}
        )

    text = _result_text(result)
    assert "mocked output" in text


@pytest.mark.asyncio
async def test_run_blocked_command_via_client(mcp_server_with_session, db_factory):
    """A command matching a BLOCK rule returns BLOCKED through Client."""
    async with db_factory() as sess:
        rule_repo = RuleRepo(sess)
        await rule_repo.create(
            pattern=r"^rm\s+-rf\s+/",
            level="block",
            description="Block dangerous rm",
            priority=0,
        )

    async with Client(mcp_server_with_session) as client:
        result = await client.call_tool(
            "ssh_run", {"command": "rm -rf /", "node": "test-node"}
        )

    text = _result_text(result)
    assert "BLOCKED" in text


@pytest.mark.asyncio
async def test_run_confirm_flow_via_client(mcp_server_with_session, db_factory):
    """CONFIRM-level command returns token request, re-call with token executes."""
    async with db_factory() as sess:
        rule_repo = RuleRepo(sess)
        await rule_repo.create(
            pattern=r"^sudo\b",
            level="confirm",
            description="Confirm sudo",
            priority=0,
        )

    async with Client(mcp_server_with_session) as client:
        result1 = await client.call_tool(
            "ssh_run", {"command": "sudo ls", "node": "test-node"}
        )
        text1 = _result_text(result1)
        assert "confirm_token" in text1

        import re

        match = re.search(r'confirm_token="([^"]+)"', text1)
        assert match, f"Could not find confirm_token in: {text1}"
        token = match.group(1)

        result2 = await client.call_tool(
            "ssh_run",
            {"command": "sudo ls", "node": "test-node", "confirm_token": token},
        )
        text2 = _result_text(result2)
        assert "mocked output" in text2


# ---------------------------------------------------------------------------
# ssh_run via Client — DB logging verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_persists_log_to_real_db(mcp_server_with_session, db_factory):
    """After ssh_run, a CommandLog row must exist in the real DB."""
    async with Client(mcp_server_with_session) as client:
        await client.call_tool("ssh_run", {"command": "whoami", "node": "test-node"})

    from sqlalchemy import select

    async with db_factory() as sess:
        result = await sess.execute(select(CommandLog))
        logs = list(result.scalars().all())

    assert len(logs) >= 1
    log = logs[-1]
    assert log.command == "whoami"
    assert log.exit_code == 0
    assert log.security_level == "allow"
    assert log.duration_ms is not None
    assert log.duration_ms >= 0


@pytest.mark.asyncio
async def test_run_persists_log_with_correct_node_id(
    mcp_server_with_session, db_factory
):
    """Log entry must reference the correct node UUID, not the name."""
    async with Client(mcp_server_with_session) as client:
        await client.call_tool("ssh_run", {"command": "pwd", "node": "test-node"})

    from sqlalchemy import select

    async with db_factory() as sess:
        node_repo = NodeRepo(sess)
        node = await node_repo.get_by_name("test-node")
        assert node is not None

        result = await sess.execute(select(CommandLog))
        logs = list(result.scalars().all())

    assert len(logs) >= 1
    assert logs[-1].node_id == node.id


# ---------------------------------------------------------------------------
# ssh_add_node via Client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_node_missing_credentials_via_client(mcp_server):
    """ssh_add_node without password or key returns an error."""
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "ssh_add_node",
            {"name": "new-node", "host": "1.2.3.4", "username": "user"},
        )

    text = _result_text(result)
    assert "Error" in text
    assert "password" in text.lower() or "private_key" in text.lower()


# ---------------------------------------------------------------------------
# ssh_run — auto-select single node
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_auto_selects_single_node(mcp_server_with_session):
    """When node is omitted and only one exists, it auto-selects."""
    async with Client(mcp_server_with_session) as client:
        result = await client.call_tool("ssh_run", {"command": "uptime"})

    text = _result_text(result)
    assert "mocked output" in text


@pytest.mark.asyncio
async def test_run_errors_with_no_node_and_multiple(
    mcp_server_with_session, db_factory
):
    """When node is omitted and multiple exist, it should error."""
    async with db_factory() as sess:
        node_repo = NodeRepo(sess)
        await node_repo.create(
            name="second-node",
            host="10.0.0.2",
            port=22,
            username="root",
            auth_type="password",
            encrypted_credential="enc",
        )

    async with Client(mcp_server_with_session) as client:
        result = await client.call_tool("ssh_run", {"command": "uptime"})

    text = _result_text(result)
    assert "cannot auto-select" in text.lower() or "Error" in text
