"""Command security primitives: SecurityLevel, CommandGuard, ConfirmTokenStore."""

from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


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


class CommandGuard:
    """Evaluates commands against security rules from the database."""

    async def evaluate(
        self,
        command: str,
        node_id: str,
        db_session: AsyncSession,
        bypass_patterns: list[str] | None = None,
    ) -> SecurityDecision:
        """Evaluate *command* against security rules fetched from the database.

        Parameters
        ----------
        command:
            The shell command string to inspect.
        node_id:
            Identifier of the target node.
        db_session:
            An async SQLAlchemy session used to query rules.
        bypass_patterns:
            A list of rule pattern strings that should be skipped
            (unless the rule is BLOCK).

        Returns
        -------
        SecurityDecision
        """
        from shuttle.db.models import SecurityRule

        query = (
            select(SecurityRule)
            .where(
                SecurityRule.enabled.is_(True),
                (SecurityRule.node_id.is_(None)) | (SecurityRule.node_id == node_id),
            )
            .order_by(SecurityRule.priority, SecurityRule.node_id.nullsfirst())
        )
        result = await db_session.execute(query)
        rules = result.scalars().all()

        # Merge: node-specific overrides global with same pattern
        seen_patterns: dict[str, SecurityRule] = {}
        for rule in rules:
            if rule.pattern in seen_patterns:
                if rule.node_id is not None:
                    seen_patterns[rule.pattern] = rule
            else:
                seen_patterns[rule.pattern] = rule

        bypassed = set(bypass_patterns or [])

        for rule in sorted(seen_patterns.values(), key=lambda r: r.priority):
            try:
                # Limit pattern length to prevent ReDoS
                if len(rule.pattern) > 500:
                    continue
                compiled = re.compile(rule.pattern)
                if compiled.search(command):
                    level = SecurityLevel(rule.level)
                    if level == SecurityLevel.BLOCK:
                        return SecurityDecision(
                            level=level,
                            matched_rule=rule.id,
                            message=f"BLOCKED: {rule.description or rule.pattern}",
                        )
                    if rule.pattern in bypassed:
                        continue
                    return SecurityDecision(
                        level=level,
                        matched_rule=rule.id,
                        message=rule.description or "",
                    )
            except re.error:
                continue

        return SecurityDecision(level=SecurityLevel.ALLOW)
