"""Tests for SSH config parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from shuttle.core.ssh_config import SSHConfigEntry, parse_ssh_config

SAMPLE_SSH_CONFIG = """\
# Global defaults
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3

Host gpu-server
    HostName 10.0.0.1
    User admin
    Port 2222
    IdentityFile ~/.ssh/gpu_key

Host dev-box
    HostName 10.0.0.2
    User ubuntu

Host bastion
    HostName 10.0.0.3
    User ec2-user
    IdentityFile ~/.ssh/id_rsa

Host staging
    HostName 10.0.0.4
    User deploy
    ProxyJump bastion

Host wildcard-?
    HostName 10.0.0.99
    User test
"""


class TestParseSSHConfig:
    """Test parse_ssh_config function."""

    def test_parse_sample_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text(SAMPLE_SSH_CONFIG)

        entries = parse_ssh_config(config_file)

        assert len(entries) == 4
        aliases = [e.alias for e in entries]
        assert "gpu-server" in aliases
        assert "dev-box" in aliases
        assert "bastion" in aliases
        assert "staging" in aliases

    def test_host_properties(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text(SAMPLE_SSH_CONFIG)

        entries = parse_ssh_config(config_file)
        by_alias = {e.alias: e for e in entries}

        gpu = by_alias["gpu-server"]
        assert gpu.hostname == "10.0.0.1"
        assert gpu.user == "admin"
        assert gpu.port == 2222
        assert gpu.identity_file == "~/.ssh/gpu_key"
        assert gpu.proxy_jump is None

    def test_default_values(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text(SAMPLE_SSH_CONFIG)

        entries = parse_ssh_config(config_file)
        by_alias = {e.alias: e for e in entries}

        dev = by_alias["dev-box"]
        assert dev.port == 22
        assert dev.identity_file is None

    def test_wildcards_skipped(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text(SAMPLE_SSH_CONFIG)

        entries = parse_ssh_config(config_file)
        aliases = [e.alias for e in entries]
        assert "wildcard-?" not in aliases
        # The global * host should also be skipped
        assert "*" not in aliases

    def test_proxy_jump_parsed(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text(SAMPLE_SSH_CONFIG)

        entries = parse_ssh_config(config_file)
        by_alias = {e.alias: e for e in entries}

        staging = by_alias["staging"]
        assert staging.proxy_jump == "bastion"

    def test_missing_config_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"
        entries = parse_ssh_config(missing)
        assert entries == []

    def test_empty_config_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text("")
        entries = parse_ssh_config(config_file)
        assert entries == []

    def test_comments_and_blank_lines(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text("# just a comment\n\n# another comment\n")
        entries = parse_ssh_config(config_file)
        assert entries == []

    def test_hostname_defaults_to_alias(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text("Host myserver\n    User root\n")
        entries = parse_ssh_config(config_file)
        assert len(entries) == 1
        assert entries[0].hostname == "myserver"
        assert entries[0].alias == "myserver"

    def test_equals_separator(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config"
        config_file.write_text(
            "Host eqhost\n    HostName=10.0.0.10\n    User=testuser\n    Port=3022\n"
        )
        entries = parse_ssh_config(config_file)
        assert len(entries) == 1
        assert entries[0].hostname == "10.0.0.10"
        assert entries[0].user == "testuser"
        assert entries[0].port == 3022


class TestSSHConfigEntry:
    """Test SSHConfigEntry.resolve_key method."""

    def test_resolve_explicit_key(self, tmp_path: Path) -> None:
        key_file = tmp_path / "my_key"
        key_file.write_text("KEY_CONTENT")

        entry = SSHConfigEntry(
            alias="test",
            hostname="10.0.0.1",
            identity_file=str(key_file),
        )
        resolved = entry.resolve_key()
        assert resolved == key_file

    def test_resolve_explicit_key_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When explicit key doesn't exist and no defaults exist, returns None."""
        # Point home to empty tmp dir so default keys don't exist
        monkeypatch.setenv("HOME", str(tmp_path))

        entry = SSHConfigEntry(
            alias="test",
            hostname="10.0.0.1",
            identity_file=str(tmp_path / "nonexistent_key"),
        )
        resolved = entry.resolve_key()
        assert resolved is None

    def test_resolve_default_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Falls back to default key paths when no explicit IdentityFile."""
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        default_key = ssh_dir / "id_ed25519"
        default_key.write_text("DEFAULT_KEY")

        monkeypatch.setenv("HOME", str(tmp_path))

        entry = SSHConfigEntry(
            alias="test",
            hostname="10.0.0.1",
        )
        resolved = entry.resolve_key()
        assert resolved is not None
        assert resolved.name == "id_ed25519"

    def test_resolve_no_keys_at_all(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns None when no keys exist anywhere."""
        monkeypatch.setenv("HOME", str(tmp_path))

        entry = SSHConfigEntry(
            alias="test",
            hostname="10.0.0.1",
        )
        resolved = entry.resolve_key()
        assert resolved is None
