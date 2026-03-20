"""Repository layer — CRUD operations for Shuttle ORM models."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.models import AppConfig, CommandLog, Node, SecurityRule, Session


class NodeRepo:
    """CRUD operations for Node records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        name: str,
        host: str,
        port: int = 22,
        username: str = "",
        auth_type: str = "password",
        encrypted_credential: str = "",
        jump_host_id: str | None = None,
        tags: list | None = None,
        pool_config: dict | None = None,
        status: str = "active",
    ) -> Node:
        node = Node(
            name=name,
            host=host,
            port=port,
            username=username,
            auth_type=auth_type,
            encrypted_credential=encrypted_credential,
            jump_host_id=jump_host_id,
            tags=tags,
            pool_config=pool_config,
            status=status,
        )
        self._session.add(node)
        await self._session.commit()
        await self._session.refresh(node)
        return node

    async def get_by_id(self, node_id: str) -> Node | None:
        result = await self._session.execute(
            select(Node).where(Node.id == node_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Node | None:
        result = await self._session.execute(
            select(Node).where(Node.name == name)
        )
        return result.scalar_one_or_none()

    async def list_all(self, tag: str | None = None) -> list[Node]:
        """List all nodes, optionally filtered by tag value."""
        stmt = select(Node)
        result = await self._session.execute(stmt)
        nodes = list(result.scalars().all())

        if tag is not None:
            nodes = [n for n in nodes if n.tags and tag in n.tags]

        return nodes

    async def update(self, node_id: str, **kwargs: Any) -> Node | None:
        node = await self.get_by_id(node_id)
        if node is None:
            return None
        for key, value in kwargs.items():
            setattr(node, key, value)
        node.updated_at = datetime.now(timezone.utc)
        await self._session.commit()
        await self._session.refresh(node)
        return node

    async def delete(self, node_id: str) -> bool:
        node = await self.get_by_id(node_id)
        if node is None:
            return False
        await self._session.delete(node)
        await self._session.commit()
        return True


class RuleRepo:
    """CRUD operations for SecurityRule records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        pattern: str,
        level: str,
        node_id: str | None = None,
        description: str | None = None,
        priority: int = 0,
        enabled: bool = True,
    ) -> SecurityRule:
        rule = SecurityRule(
            pattern=pattern,
            level=level,
            node_id=node_id,
            description=description,
            priority=priority,
            enabled=enabled,
        )
        self._session.add(rule)
        await self._session.commit()
        await self._session.refresh(rule)
        return rule

    async def get_by_id(self, rule_id: str) -> SecurityRule | None:
        result = await self._session.execute(
            select(SecurityRule).where(SecurityRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, node_id: str | None = None) -> list[SecurityRule]:
        """List rules ordered by priority, optionally filtered by node."""
        stmt = select(SecurityRule).order_by(SecurityRule.priority)
        if node_id is not None:
            stmt = stmt.where(SecurityRule.node_id == node_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, rule_id: str, **kwargs: Any) -> SecurityRule | None:
        rule = await self.get_by_id(rule_id)
        if rule is None:
            return None
        for key, value in kwargs.items():
            setattr(rule, key, value)
        await self._session.commit()
        await self._session.refresh(rule)
        return rule

    async def delete(self, rule_id: str) -> bool:
        rule = await self.get_by_id(rule_id)
        if rule is None:
            return False
        await self._session.delete(rule)
        await self._session.commit()
        return True

    async def reorder(self, ids: list[str]) -> None:
        """Assign new priorities based on position in the ids list.

        The first id in the list gets priority 0, the second gets 1, etc.
        """
        for index, rule_id in enumerate(ids):
            rule = await self.get_by_id(rule_id)
            if rule is not None:
                rule.priority = index
        await self._session.commit()


class SessionRepo:
    """CRUD operations for Session records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        node_id: str,
        working_directory: str | None = None,
        env_vars: dict | None = None,
        status: str = "active",
    ) -> Session:
        sess = Session(
            node_id=node_id,
            working_directory=working_directory,
            env_vars=env_vars,
            status=status,
        )
        self._session.add(sess)
        await self._session.commit()
        await self._session.refresh(sess)
        return sess

    async def get_by_id(self, session_id: str) -> Session | None:
        result = await self._session.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Session]:
        result = await self._session.execute(
            select(Session).where(Session.status == "active")
        )
        return list(result.scalars().all())

    async def close(self, session_id: str) -> Session | None:
        sess = await self.get_by_id(session_id)
        if sess is None:
            return None
        sess.status = "closed"
        sess.closed_at = datetime.now(timezone.utc)
        await self._session.commit()
        await self._session.refresh(sess)
        return sess

    async def update_working_dir(
        self, session_id: str, working_directory: str
    ) -> Session | None:
        sess = await self.get_by_id(session_id)
        if sess is None:
            return None
        sess.working_directory = working_directory
        await self._session.commit()
        await self._session.refresh(sess)
        return sess


class LogRepo:
    """CRUD operations for CommandLog records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        node_id: str,
        command: str,
        session_id: str | None = None,
        exit_code: int | None = None,
        stdout: str | None = None,
        stderr: str | None = None,
        security_level: str | None = None,
        security_rule_id: str | None = None,
        bypassed: bool = False,
        duration_ms: int | None = None,
    ) -> CommandLog:
        log = CommandLog(
            session_id=session_id,
            node_id=node_id,
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            security_level=security_level,
            security_rule_id=security_rule_id,
            bypassed=bypassed,
            duration_ms=duration_ms,
        )
        self._session.add(log)
        await self._session.commit()
        await self._session.refresh(log)
        return log

    async def list_by_session(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CommandLog]:
        """List command logs for a session, paginated."""
        result = await self._session.execute(
            select(CommandLog)
            .where(CommandLog.session_id == session_id)
            .order_by(CommandLog.executed_at)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


class ConfigRepo:
    """Key-value configuration store using AppConfig."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str) -> Any:
        """Retrieve a configuration value by key. Returns None if not found."""
        result = await self._session.execute(
            select(AppConfig).where(AppConfig.key == key)
        )
        record = result.scalar_one_or_none()
        return record.value if record is not None else None

    async def set(self, key: str, value: Any) -> AppConfig:
        """Upsert a configuration value."""
        record = await self._session.execute(
            select(AppConfig).where(AppConfig.key == key)
        )
        existing = record.scalar_one_or_none()
        if existing is not None:
            existing.value = value
            existing.updated_at = datetime.now(timezone.utc)
            await self._session.commit()
            await self._session.refresh(existing)
            return existing
        else:
            new_record = AppConfig(key=key, value=value)
            self._session.add(new_record)
            await self._session.commit()
            await self._session.refresh(new_record)
            return new_record
