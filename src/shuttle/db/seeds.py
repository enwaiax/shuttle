"""Default security rule seeds for Shuttle.

These rules are inserted on first startup if no rules exist in the database.
"""

from __future__ import annotations

DEFAULT_SECURITY_RULES = [
    # Block
    {"pattern": r"^rm -rf /$", "level": "block", "description": "Remove root filesystem", "priority": 1},
    {"pattern": r"mkfs\.", "level": "block", "description": "Format filesystem", "priority": 2},
    {"pattern": r"dd if=.* of=/dev/", "level": "block", "description": "Raw disk write", "priority": 3},
    {"pattern": r":\(\)\{.*:\|:&\};:", "level": "block", "description": "Fork bomb", "priority": 4},
    # Confirm
    {"pattern": r"sudo .*", "level": "confirm", "description": "Sudo commands", "priority": 10},
    {"pattern": r"rm -rf ", "level": "confirm", "description": "Recursive force delete", "priority": 11},
    {"pattern": r"chmod 777", "level": "confirm", "description": "World-writable permissions", "priority": 12},
    {"pattern": r"shutdown", "level": "confirm", "description": "System shutdown", "priority": 13},
    {"pattern": r"reboot", "level": "confirm", "description": "System reboot", "priority": 14},
    {"pattern": r"kill -9", "level": "confirm", "description": "Force kill process", "priority": 15},
    # Warn
    {"pattern": r"apt install", "level": "warn", "description": "APT package install", "priority": 20},
    {"pattern": r"pip install", "level": "warn", "description": "Pip package install", "priority": 21},
    {"pattern": r"npm install", "level": "warn", "description": "NPM package install", "priority": 22},
    {"pattern": r"curl .* \| bash", "level": "warn", "description": "Piped remote script", "priority": 23},
]


async def seed_default_rules(session) -> int:
    """Insert default security rules if none exist.

    Parameters
    ----------
    session:
        An open SQLAlchemy async session.

    Returns
    -------
    int
        The number of rules inserted (0 if rules already existed).
    """
    from shuttle.db.repository import RuleRepo

    repo = RuleRepo(session)
    existing = await repo.list_all()
    if existing:
        return 0
    count = 0
    for rule_data in DEFAULT_SECURITY_RULES:
        await repo.create(**rule_data)
        count += 1
    return count
