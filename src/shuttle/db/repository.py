"""Repository layer — CRUD operations for Shuttle ORM models."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shuttle.db.models import (
    AppConfig,
    ApprovalRequest,
    CommandLog,
    Node,
    SecurityRule,
    Session,
)


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
        status: str = "inactive",
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
        result = await self._session.execute(select(Node).where(Node.id == node_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Node | None:
        result = await self._session.execute(select(Node).where(Node.name == name))
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
        node.updated_at = datetime.now(UTC)
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
        source_rule_id: str | None = None,
    ) -> SecurityRule:
        rule = SecurityRule(
            pattern=pattern,
            level=level,
            node_id=node_id,
            description=description,
            priority=priority,
            enabled=enabled,
            source_rule_id=source_rule_id,
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

    async def list_effective(self, node_id: str) -> list["SecurityRule"]:
        """Return merged global + node-specific rules. Node rules override globals with same pattern."""
        global_q = (
            select(SecurityRule)
            .where(SecurityRule.node_id.is_(None))
            .order_by(SecurityRule.priority)
        )
        global_result = await self._session.execute(global_q)
        global_rules = list(global_result.scalars().all())

        node_q = (
            select(SecurityRule)
            .where(SecurityRule.node_id == node_id)
            .order_by(SecurityRule.priority)
        )
        node_result = await self._session.execute(node_q)
        node_rules = list(node_result.scalars().all())

        node_patterns = {r.pattern for r in node_rules}
        merged = [r for r in global_rules if r.pattern not in node_patterns]
        merged.extend(node_rules)
        merged.sort(key=lambda r: r.priority)
        return merged

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
        actor_id: str = "anonymous",
        client_id: str = "mcp",
        conversation_id: str = "default",
    ) -> Session:
        sess = Session(
            node_id=node_id,
            working_directory=working_directory,
            env_vars=env_vars,
            status=status,
            actor_id=actor_id,
            client_id=client_id,
            conversation_id=conversation_id,
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
        sess.closed_at = datetime.now(UTC)
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
        action: str = "command",
        actor_id: str = "anonymous",
        client_id: str = "mcp",
        conversation_id: str = "default",
        approval_id: str | None = None,
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
            action=action,
            actor_id=actor_id,
            client_id=client_id,
            conversation_id=conversation_id,
            approval_id=approval_id,
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

    async def list_by_node(
        self,
        node_id: str,
        limit: int = 20,
    ) -> list[CommandLog]:
        """List recent command logs for a node, newest first."""
        result = await self._session.execute(
            select(CommandLog)
            .where(CommandLog.node_id == node_id)
            .order_by(CommandLog.executed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class ApprovalRepo:
    """Persistence and atomic state transitions for human approvals."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _is_expired(request: ApprovalRequest, now: datetime) -> bool:
        expires_at = request.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= now

    async def create(self, **kwargs: Any) -> ApprovalRequest:
        request = ApprovalRequest(**kwargs)
        self._session.add(request)
        await self._session.commit()
        await self._session.refresh(request)
        return request

    async def get_by_id(self, approval_id: str) -> ApprovalRequest | None:
        result = await self._session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        )
        return result.scalar_one_or_none()

    async def list(self, status: str | None = None) -> list[ApprovalRequest]:
        stmt = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
        if status is not None:
            stmt = stmt.where(ApprovalRequest.status == status)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def decide(
        self,
        approval_id: str,
        *,
        approve: bool,
        approver: str,
        reason: str | None = None,
    ) -> ApprovalRequest | None:
        request = await self.get_by_id(approval_id)
        if request is None or request.status != "pending":
            return None
        now = datetime.now(UTC)
        if self._is_expired(request, now):
            request.status = "expired"
        else:
            request.status = "approved" if approve else "denied"
            request.approver = approver
            request.decision_reason = reason
            request.decided_at = now
        await self._session.commit()
        await self._session.refresh(request)
        return request

    async def consume(self, approval_id: str) -> ApprovalRequest | None:
        request = await self.get_by_id(approval_id)
        now = datetime.now(UTC)
        if (
            request is None
            or request.status != "approved"
            or request.consumed_at is not None
            or self._is_expired(request, now)
        ):
            if request is not None and self._is_expired(request, now):
                request.status = "expired"
                await self._session.commit()
            return None
        request.status = "consumed"
        request.consumed_at = now
        await self._session.commit()
        await self._session.refresh(request)
        return request


async def cleanup_old_data(
    session: AsyncSession,
    command_log_days: int = 30,
    closed_session_days: int = 7,
) -> dict[str, int]:
    """Delete old command logs and closed sessions based on retention policy.

    Returns dict with counts of deleted records.
    """
    from sqlalchemy import delete

    cutoff_logs = datetime.now(UTC) - timedelta(days=command_log_days)
    cutoff_sessions = datetime.now(UTC) - timedelta(days=closed_session_days)

    # Delete old command logs
    result_logs = await session.execute(
        delete(CommandLog).where(CommandLog.executed_at < cutoff_logs)
    )
    deleted_logs = result_logs.rowcount or 0

    # Delete old closed sessions
    result_sessions = await session.execute(
        delete(Session).where(
            Session.status == "closed",
            Session.closed_at < cutoff_sessions,
        )
    )
    deleted_sessions = result_sessions.rowcount or 0

    await session.commit()
    return {"command_logs": deleted_logs, "sessions": deleted_sessions}


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
            existing.updated_at = datetime.now(UTC)
            await self._session.commit()
            await self._session.refresh(existing)
            return existing
        else:
            new_record = AppConfig(key=key, value=value)
            self._session.add(new_record)
            await self._session.commit()
            await self._session.refresh(new_record)
            return new_record
