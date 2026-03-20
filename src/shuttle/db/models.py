"""SQLAlchemy 2.0 ORM models for Shuttle."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Node(Base):
    """SSH node / host connection configuration."""

    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted_credential: Mapped[str] = mapped_column(Text, nullable=False)
    jump_host_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("nodes.id"), nullable=True
    )
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    pool_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Self-referential relationship for jump host
    jump_host: Mapped["Node | None"] = relationship(
        "Node", remote_side="Node.id", foreign_keys=[jump_host_id]
    )

    # Relationships
    security_rules: Mapped[list["SecurityRule"]] = relationship(
        "SecurityRule", back_populates="node", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="node", cascade="all, delete-orphan"
    )
    command_logs: Mapped[list["CommandLog"]] = relationship(
        "CommandLog", back_populates="node", cascade="all, delete-orphan"
    )


class SecurityRule(Base):
    """Pattern-based security rule for command filtering."""

    __tablename__ = "security_rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=False)
    node_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("nodes.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_rule_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    node: Mapped["Node | None"] = relationship("Node", back_populates="security_rules")


class Session(Base):
    """Active SSH session tracking."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("nodes.id"), nullable=False
    )
    working_directory: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    env_vars: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    node: Mapped["Node"] = relationship("Node", back_populates="sessions")
    command_logs: Mapped[list["CommandLog"]] = relationship(
        "CommandLog", back_populates="session"
    )


class CommandLog(Base):
    """Log of executed commands."""

    __tablename__ = "command_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # session_id is NULLABLE — supports stateless execution without a session
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=True
    )
    node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("nodes.id"), nullable=False
    )
    command: Mapped[str] = mapped_column(Text, nullable=False)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    security_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    security_rule_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    bypassed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["Session | None"] = relationship(
        "Session", back_populates="command_logs"
    )
    node: Mapped["Node"] = relationship("Node", back_populates="command_logs")


class AppConfig(Base):
    """Application key-value configuration store."""

    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
