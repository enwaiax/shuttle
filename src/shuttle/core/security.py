"""Command security primitives: SecurityLevel, CommandGuard, ConfirmTokenStore."""

import re
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SecurityLevel(str, Enum):
    """Severity levels used when evaluating a command against security rules."""

    BLOCK = "block"
    CONFIRM = "confirm"
    WARN = "warn"
    ALLOW = "allow"


@dataclass
class SecurityDecision:
    """The result produced by CommandGuard.evaluate()."""

    level: SecurityLevel
    matched_rule: Optional[str] = None
    message: str = ""


# ---------------------------------------------------------------------------
# ConfirmTokenStore
# ---------------------------------------------------------------------------

_CLEANUP_THRESHOLD = 100


class ConfirmTokenStore:
    """In-memory store for one-time confirmation tokens with TTL.

    Tokens are generated per (command, node_id) pair.  Validating a token
    consumes it (one-time use).  Expired tokens are pruned lazily when the
    store grows beyond *_CLEANUP_THRESHOLD* entries.
    """

    def __init__(self, ttl: float = 300.0) -> None:
        self._ttl = ttl
        # token -> (command, node_id, expires_at)
        self._store: dict[str, tuple[str, str, float]] = {}

    def _maybe_cleanup(self) -> None:
        """Remove expired tokens if the store is getting large."""
        if len(self._store) > _CLEANUP_THRESHOLD:
            now = time.monotonic()
            expired = [t for t, (_, _, exp) in self._store.items() if exp <= now]
            for t in expired:
                del self._store[t]

    def create(self, command: str, node_id: str) -> str:
        """Create and store a one-time token for the given (command, node_id)."""
        self._maybe_cleanup()
        token = secrets.token_urlsafe(32)
        self._store[token] = (command, node_id, time.monotonic() + self._ttl)
        return token

    def validate(self, token: str, command: str, node_id: str) -> bool:
        """Validate *and consume* a token.  Returns False if missing, expired, or mismatched."""
        entry = self._store.get(token)
        if entry is None:
            return False
        stored_command, stored_node_id, expires_at = entry
        # Always consume the token regardless of outcome
        del self._store[token]
        if time.monotonic() > expires_at:
            return False
        return stored_command == command and stored_node_id == node_id


# ---------------------------------------------------------------------------
# CommandGuard
# ---------------------------------------------------------------------------

@dataclass
class _CompiledRule:
    pattern: re.Pattern
    pattern_str: str
    level: SecurityLevel
    name: str
    priority: int
    message: str
    enabled: bool


class CommandGuard:
    """Evaluates shell commands against a prioritised list of security rules.

    Rules are matched in ascending priority order (lower number = higher
    priority).  The first match wins.  If no rule matches, the decision is
    ALLOW with no matched rule.
    """

    def __init__(self) -> None:
        self._rules: list[_CompiledRule] = []

    def load_rules(self, rules: list[dict]) -> None:
        """Compile and store rules from a list of dicts.

        Each dict may contain:
            name (str)          — human-readable identifier
            pattern (str)       — regular-expression string (required)
            level (str)         — one of block/confirm/warn/allow (required)
            priority (int)      — lower = evaluated first (default 100)
            message (str)       — optional explanation shown to the caller
            enabled (bool)      — if False the rule is ignored (default True)

        Raises ValueError if a pattern is not a valid regular expression.
        """
        compiled: list[_CompiledRule] = []
        for rule in rules:
            pattern_str: str = rule["pattern"]
            try:
                pattern = re.compile(pattern_str)
            except re.error as exc:
                raise ValueError(
                    f"Invalid regex pattern {pattern_str!r}: {exc}"
                ) from exc

            level = SecurityLevel(rule["level"])
            compiled.append(
                _CompiledRule(
                    pattern=pattern,
                    pattern_str=pattern_str,
                    level=level,
                    name=rule.get("name", pattern_str),
                    priority=int(rule.get("priority", 100)),
                    message=rule.get("message", ""),
                    enabled=bool(rule.get("enabled", True)),
                )
            )

        compiled.sort(key=lambda r: r.priority)
        self._rules = compiled

    def evaluate(
        self,
        command: str,
        node_id: str,
        bypass_patterns: Optional[list[str]] = None,
    ) -> SecurityDecision:
        """Evaluate *command* against the loaded rules.

        Parameters
        ----------
        command:
            The shell command string to inspect.
        node_id:
            Identifier of the target node (reserved for future per-node rules).
        bypass_patterns:
            A list of rule pattern strings whose level should be downgraded to
            ALLOW.  BLOCK rules can NEVER be bypassed.

        Returns
        -------
        SecurityDecision
        """
        bypass_patterns = bypass_patterns or []

        for rule in self._rules:
            if not rule.enabled:
                continue
            if not rule.pattern.search(command):
                continue

            # BLOCK is absolute — cannot be bypassed
            if rule.level == SecurityLevel.BLOCK:
                return SecurityDecision(
                    level=SecurityLevel.BLOCK,
                    matched_rule=rule.name,
                    message=rule.message or f"Command blocked by rule '{rule.name}'",
                )

            # Bypass: if the pattern string appears in bypass_patterns, treat as ALLOW
            if rule.pattern_str in bypass_patterns:
                return SecurityDecision(
                    level=SecurityLevel.ALLOW,
                    matched_rule=rule.name,
                    message=f"Rule '{rule.name}' bypassed",
                )

            return SecurityDecision(
                level=rule.level,
                matched_rule=rule.name,
                message=rule.message,
            )

        # No rule matched
        return SecurityDecision(level=SecurityLevel.ALLOW)
