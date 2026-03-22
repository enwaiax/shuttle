"""Tests for SSH connection helpers (NodeConnectInfo, connect_ssh, kwargs builder)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shuttle.core.proxy import NodeConnectInfo, _build_connect_kwargs, connect_ssh


def test_build_connect_kwargs_minimal() -> None:
    info = NodeConnectInfo(node_id="n1", hostname="h.example", username="u")
    kw = _build_connect_kwargs(info)
    assert kw["host"] == "h.example"
    assert kw["port"] == 22
    assert kw["username"] == "u"
    assert kw["connect_timeout"] == 30.0
    assert kw["known_hosts"] is None


def test_build_connect_kwargs_password_and_known_hosts() -> None:
    info = NodeConnectInfo(
        node_id="n1",
        hostname="10.0.0.1",
        username="root",
        port=2222,
        password="secret",
        known_hosts="/etc/ssh/known_hosts",
        connect_timeout=5.0,
    )
    kw = _build_connect_kwargs(info)
    assert kw["password"] == "secret"
    assert kw["known_hosts"] == "/etc/ssh/known_hosts"
    assert kw["port"] == 2222
    assert kw["connect_timeout"] == 5.0


def test_build_connect_kwargs_private_key_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_key = object()
    monkeypatch.setattr(
        "shuttle.core.proxy.asyncssh.import_private_key",
        lambda pem: fake_key if pem == "PEM" else None,
    )
    info = NodeConnectInfo(
        node_id="n1",
        hostname="h",
        username="u",
        private_key="PEM",
    )
    kw = _build_connect_kwargs(info)
    assert kw["client_keys"] == [fake_key]


def test_build_connect_kwargs_extra_options_override() -> None:
    info = NodeConnectInfo(
        node_id="n1",
        hostname="h",
        username="u",
        extra_options={"port": 99, "compression_algs": ()},
    )
    kw = _build_connect_kwargs(info)
    assert kw["port"] == 99
    assert kw["compression_algs"] == ()


@pytest.mark.asyncio
async def test_connect_ssh_direct_calls_asyncssh_connect() -> None:
    info = NodeConnectInfo(node_id="n1", hostname="h", username="u")
    mock_conn = MagicMock()
    with patch(
        "shuttle.core.proxy.asyncssh.connect", new_callable=AsyncMock
    ) as mock_connect:
        mock_connect.return_value = mock_conn
        out = await connect_ssh(info)
    assert out is mock_conn
    mock_connect.assert_awaited_once()
    call_kw = mock_connect.await_args.kwargs
    assert call_kw["host"] == "h"


@pytest.mark.asyncio
async def test_connect_ssh_with_jump_host_sets_tunnel() -> None:
    target = NodeConnectInfo(
        node_id="target",
        hostname="10.0.0.2",
        username="u",
        jump_host=NodeConnectInfo(
            node_id="jump",
            hostname="10.0.0.1",
            username="j",
        ),
    )
    jump_conn = MagicMock(name="jump")
    target_conn = MagicMock(name="target")

    async def connect_side(**kwargs):
        if kwargs.get("tunnel") is jump_conn:
            return target_conn
        if "tunnel" not in kwargs:
            return jump_conn
        raise AssertionError("unexpected connect kwargs")

    with patch(
        "shuttle.core.proxy.asyncssh.connect",
        new_callable=AsyncMock,
        side_effect=connect_side,
    ):
        out = await connect_ssh(target)

    assert out is target_conn
