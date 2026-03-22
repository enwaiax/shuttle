"""Extra tests for seed_default_rules branches."""

import pytest

from shuttle.db.repository import RuleRepo
from shuttle.db.seeds import seed_default_rules


@pytest.mark.asyncio
async def test_seed_default_rules_returns_zero_when_rules_exist(db_session):
    repo = RuleRepo(db_session)
    await repo.create(pattern="x", level="allow", priority=0)
    n = await seed_default_rules(db_session)
    assert n == 0
