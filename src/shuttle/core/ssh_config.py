"""Parse ~/.ssh/config into structured entries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_KEY_PATHS = [
    "~/.ssh/id_ed25519",
    "~/.ssh/id_rsa",
    "~/.ssh/id_ecdsa",
]

# Keyword and value are separated by whitespace or `=` (optionally spaced).
# The value captures the rest of the line so quoted paths with spaces survive.
_LINE_RE = re.compile(r"^(\S+?)(?:\s*=\s*|\s+)(.*)$")


def _unquote(value: str) -> str:
    """Strip a single pair of matching outer quotes, as ssh(1) does."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


@dataclass
class SSHConfigEntry:
    alias: str
    hostname: str
    user: str = "root"
    port: int = 22
    identity_file: str | None = None
    proxy_jump: str | None = None

    def resolve_key(self) -> Path | None:
        """Find the private key file. Checks explicit IdentityFile first, then defaults."""
        if self.identity_file:
            path = Path(self.identity_file).expanduser()
            if path.exists():
                return path
        # Fallback: SSH default key paths
        for default in DEFAULT_KEY_PATHS:
            path = Path(default).expanduser()
            if path.exists():
                return path
        return None


def parse_ssh_config(path: Path | None = None) -> list[SSHConfigEntry]:
    """Parse an SSH config file into a list of host entries.

    Skips wildcard hosts (* patterns).
    """
    if path is None:
        path = Path.home() / ".ssh" / "config"

    if not path.exists():
        return []

    entries: list[SSHConfigEntry] = []
    current: dict[str, str] = {}

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = _LINE_RE.match(line)
        if not match:
            continue

        key, value = match.group(1), _unquote(match.group(2))
        if not value:
            continue

        if key.lower() == "host":
            # Save previous entry
            if current and "alias" in current:
                entries.append(_build_entry(current))
            # Start new entry (skip wildcards)
            if "*" in value or "?" in value:
                current = {}
            else:
                current = {"alias": value}
        elif current:
            current[key.lower()] = value

    # Don't forget last entry
    if current and "alias" in current:
        entries.append(_build_entry(current))

    return entries


def _build_entry(data: dict[str, str]) -> SSHConfigEntry:
    return SSHConfigEntry(
        alias=data["alias"],
        hostname=data.get("hostname", data["alias"]),
        user=data.get("user", "root"),
        port=int(data.get("port", "22")),
        identity_file=data.get("identityfile"),
        proxy_jump=data.get("proxyjump"),
    )
