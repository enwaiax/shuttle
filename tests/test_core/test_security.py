"""Tests for CommandGuard and ConfirmTokenStore."""

import time

import pytest

from shuttle.core.security import (
    CommandGuard,
    ConfirmTokenStore,
    SecurityLevel,
)

# ---------------------------------------------------------------------------
# SecurityLevel enum
# ---------------------------------------------------------------------------


def test_security_level_values():
    """SecurityLevel must expose the four expected string values."""
    assert SecurityLevel.BLOCK == "block"
    assert SecurityLevel.CONFIRM == "confirm"
    assert SecurityLevel.WARN == "warn"
    assert SecurityLevel.ALLOW == "allow"


# ---------------------------------------------------------------------------
# CommandGuard helpers
# ---------------------------------------------------------------------------

SAMPLE_RULES = [
    {"name": "block-rm-rf", "pattern": r"rm\s+-rf\s+/", "level": "block", "priority": 10},
    {"name": "confirm-sudo", "pattern": r"\bsudo\b", "level": "confirm", "priority": 20},
    {"name": "warn-curl", "pattern": r"\bcurl\b", "level": "warn", "priority": 30},
    {"name": "allow-ls", "pattern": r"^ls\b", "level": "allow", "priority": 40},
]


def _guard(rules=None) -> CommandGuard:
    g = CommandGuard()
    g.load_rules(rules if rules is not None else SAMPLE_RULES)
    return g


# ---------------------------------------------------------------------------
# CommandGuard tests
# ---------------------------------------------------------------------------


def test_block_command():
    """A command matching a BLOCK rule must be blocked."""
    g = _guard()
    decision = g.evaluate("rm -rf /home", "node1")
    assert decision.level == SecurityLevel.BLOCK
    assert decision.matched_rule == "block-rm-rf"


def test_confirm_command():
    """A command matching a CONFIRM rule must require confirmation."""
    g = _guard()
    decision = g.evaluate("sudo apt-get update", "node1")
    assert decision.level == SecurityLevel.CONFIRM
    assert decision.matched_rule == "confirm-sudo"


def test_warn_command():
    """A command matching a WARN rule must emit a warning."""
    g = _guard()
    decision = g.evaluate("curl https://example.com", "node1")
    assert decision.level == SecurityLevel.WARN
    assert decision.matched_rule == "warn-curl"


def test_allow_command():
    """A command matching an ALLOW rule must be allowed."""
    g = _guard()
    decision = g.evaluate("ls -la", "node1")
    assert decision.level == SecurityLevel.ALLOW
    assert decision.matched_rule == "allow-ls"


def test_no_match_defaults_to_allow():
    """A command that matches no rule must default to ALLOW."""
    g = _guard()
    decision = g.evaluate("echo hello", "node1")
    assert decision.level == SecurityLevel.ALLOW
    assert decision.matched_rule is None


def test_bypass_patterns_skip_confirm_but_not_block():
    """bypass_patterns can downgrade CONFIRM to ALLOW, but BLOCK is never bypassed."""
    g = _guard()

    # CONFIRM bypassed → ALLOW
    decision = g.evaluate(
        "sudo apt-get update", "node1", bypass_patterns=[r"\bsudo\b"]
    )
    assert decision.level == SecurityLevel.ALLOW

    # BLOCK NOT bypassed even when pattern listed
    decision = g.evaluate(
        "rm -rf /home", "node1", bypass_patterns=[r"rm\s+-rf\s+/"]
    )
    assert decision.level == SecurityLevel.BLOCK


def test_disabled_rule_ignored():
    """Rules with enabled=False must not match any command."""
    rules = [
        {
            "name": "disabled-block",
            "pattern": r"echo",
            "level": "block",
            "priority": 1,
            "enabled": False,
        }
    ]
    g = _guard(rules)
    decision = g.evaluate("echo hello", "node1")
    assert decision.level == SecurityLevel.ALLOW


def test_invalid_regex_rejected():
    """load_rules must raise ValueError for an invalid regex pattern."""
    g = CommandGuard()
    with pytest.raises(ValueError, match="Invalid regex"):
        g.load_rules([{"name": "bad", "pattern": r"[invalid", "level": "block"}])


# ---------------------------------------------------------------------------
# ConfirmTokenStore tests
# ---------------------------------------------------------------------------


def test_token_create_and_validate():
    """A freshly created token must validate successfully."""
    store = ConfirmTokenStore()
    token = store.create("sudo reboot", "node42")
    assert store.validate(token, "sudo reboot", "node42") is True


def test_token_is_one_time():
    """A token must not be valid after it has been consumed once."""
    store = ConfirmTokenStore()
    token = store.create("sudo reboot", "node42")
    assert store.validate(token, "sudo reboot", "node42") is True
    assert store.validate(token, "sudo reboot", "node42") is False


def test_token_wrong_command():
    """A token must not validate if the command differs."""
    store = ConfirmTokenStore()
    token = store.create("sudo reboot", "node42")
    assert store.validate(token, "sudo halt", "node42") is False


def test_token_wrong_node():
    """A token must not validate if the node_id differs."""
    store = ConfirmTokenStore()
    token = store.create("sudo reboot", "node42")
    assert store.validate(token, "sudo reboot", "node99") is False


def test_token_expired():
    """A token used after its TTL must not validate."""
    store = ConfirmTokenStore(ttl=0.01)  # 10 ms TTL
    token = store.create("sudo reboot", "node42")
    time.sleep(0.05)
    assert store.validate(token, "sudo reboot", "node42") is False
