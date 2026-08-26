"""Session identity isolation tests."""

from unittest.mock import MagicMock

from shuttle.core.session import SessionManager, SSHSession


def test_find_active_requires_complete_actor_boundary() -> None:
    manager = SessionManager(pool=MagicMock())
    claude = SSHSession(
        session_id="claude-1",
        node_id="gpu-1",
        actor_id="alice",
        client_id="claude-code",
        conversation_id="conv-a",
    )
    codex = SSHSession(
        session_id="codex-1",
        node_id="gpu-1",
        actor_id="alice",
        client_id="codex",
        conversation_id="conv-b",
    )
    manager._sessions = {claude.session_id: claude, codex.session_id: codex}

    assert (
        manager.find_active(
            "gpu-1",
            actor_id="alice",
            client_id="claude-code",
            conversation_id="conv-a",
        )
        is claude
    )
    assert (
        manager.find_active(
            "gpu-1",
            actor_id="alice",
            client_id="claude-code",
            conversation_id="conv-b",
        )
        is None
    )
