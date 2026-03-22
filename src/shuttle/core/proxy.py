"""SSH proxy primitives: NodeConnectInfo dataclass and connect_ssh function.

Supports direct connections and connections via a Jump Host (bastion) using
asyncssh's tunnel parameter.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import asyncssh


@dataclass
class NodeConnectInfo:
    """All the information needed to open an SSH connection to a node.

    Attributes
    ----------
    node_id:
        Logical identifier for the node (e.g. "prod-web-01").
    hostname:
        Resolvable hostname or IP address of the target host.
    port:
        SSH port on the target host (default 22).
    username:
        Remote login username.
    password:
        Optional plaintext password.  Mutually exclusive with private_key.
    private_key:
        Optional PEM-encoded private key string.
    known_hosts:
        Path to a known_hosts file, or None to disable host-key checking.
    jump_host:
        Optional NodeConnectInfo describing the jump / bastion host to tunnel
        through before reaching this node.
    connect_timeout:
        Seconds to wait for the TCP+SSH handshake to complete (default 30).
    extra_options:
        Arbitrary asyncssh keyword arguments forwarded verbatim to
        ``asyncssh.connect()``.
    """

    node_id: str
    hostname: str
    username: str
    port: int = 22
    password: str | None = None
    private_key: str | None = None
    known_hosts: str | None = None
    jump_host: NodeConnectInfo | None = None
    connect_timeout: float = 30.0
    extra_options: dict = field(default_factory=dict)


async def connect_ssh(info: NodeConnectInfo) -> asyncssh.SSHClientConnection:
    """Open an asyncssh connection described by *info*.

    If *info.jump_host* is set, a tunnel is first established to the jump host
    and the target connection is created through that tunnel.

    Parameters
    ----------
    info:
        Connection parameters for the target node.

    Returns
    -------
    asyncssh.SSHClientConnection
        An open SSH connection to the target.  The caller is responsible for
        closing it.
    """
    kwargs = _build_connect_kwargs(info)

    if info.jump_host is not None:
        tunnel_conn = await connect_ssh(info.jump_host)
        kwargs["tunnel"] = tunnel_conn

    return await asyncssh.connect(**kwargs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_connect_kwargs(info: NodeConnectInfo) -> dict:
    """Build the keyword-argument dict for ``asyncssh.connect()``."""
    kwargs: dict = {
        "host": info.hostname,
        "port": info.port,
        "username": info.username,
        "connect_timeout": info.connect_timeout,
    }

    if info.password is not None:
        kwargs["password"] = info.password

    if info.private_key is not None:
        kwargs["client_keys"] = [asyncssh.import_private_key(info.private_key)]

    if info.known_hosts is not None:
        kwargs["known_hosts"] = info.known_hosts
    else:
        # Disable host-key verification when no known_hosts is provided.
        kwargs["known_hosts"] = None

    # Forward any caller-supplied overrides last so they can override defaults.
    kwargs.update(info.extra_options)

    return kwargs
