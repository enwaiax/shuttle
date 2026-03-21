"""Pydantic request/response schemas for the Web API."""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Nodes ──────────────────────────────────────────


class NodeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    auth_type: str = Field("password", pattern=r"^(password|key)$")
    credential: str = Field(
        ..., min_length=1, description="Plaintext password or key content"
    )
    jump_host_id: str | None = None
    tags: list[str] | None = None


class NodeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    host: str | None = Field(None, min_length=1, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    username: str | None = Field(None, min_length=1, max_length=255)
    auth_type: str | None = Field(None, pattern=r"^(password|key)$")
    credential: str | None = None
    jump_host_id: str | None = None
    tags: list[str] | None = None


class NodeResponse(BaseModel):
    id: str
    name: str
    host: str
    port: int
    username: str
    auth_type: str
    jump_host_id: str | None
    tags: list[str] | None
    status: str
    latency_ms: int | None = None
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NodeTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: float | None = None


# ── Security Rules ─────────────────────────────────


class RuleCreate(BaseModel):
    pattern: str = Field(..., min_length=1)
    level: str = Field(..., pattern=r"^(block|confirm|warn|allow)$")
    node_id: str | None = None
    description: str | None = None
    priority: int = 0
    enabled: bool = True
    source_rule_id: str | None = None


class RuleUpdate(BaseModel):
    pattern: str | None = None
    level: str | None = Field(None, pattern=r"^(block|confirm|warn|allow)$")
    node_id: str | None = None
    description: str | None = None
    priority: int | None = None
    enabled: bool | None = None


class RuleResponse(BaseModel):
    id: str
    pattern: str
    level: str
    node_id: str | None
    description: str | None
    priority: int
    enabled: bool
    source_rule_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RuleReorderRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1)


# ── Sessions ───────────────────────────────────────


class SessionResponse(BaseModel):
    id: str
    node_id: str
    node_name: str | None = None
    working_directory: str | None
    status: str
    created_at: datetime
    closed_at: datetime | None

    model_config = {"from_attributes": True}


# ── Command Logs ───────────────────────────────────


class CommandLogResponse(BaseModel):
    id: str
    session_id: str | None
    node_id: str
    node_name: str | None = None
    command: str
    exit_code: int | None
    stdout: str | None
    stderr: str | None
    security_level: str | None
    bypassed: bool
    duration_ms: int | None
    executed_at: datetime

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    items: list[CommandLogResponse]
    total: int
    page: int
    page_size: int


# ── Settings ───────────────────────────────────────


class SettingsResponse(BaseModel):
    pool_max_total: int = 50
    pool_max_per_node: int = 5
    pool_idle_timeout: int = 300
    pool_max_lifetime: int = 3600
    pool_queue_size: int = 10
    cleanup_command_logs_days: int = 30
    cleanup_closed_sessions_days: int = 7


class SettingsUpdate(BaseModel):
    pool_max_total: int | None = None
    pool_max_per_node: int | None = None
    pool_idle_timeout: int | None = None
    pool_max_lifetime: int | None = None
    pool_queue_size: int | None = None
    cleanup_command_logs_days: int | None = None
    cleanup_closed_sessions_days: int | None = None


# ── Stats ──────────────────────────────────────────


class StatsResponse(BaseModel):
    node_count: int
    active_sessions: int
    total_commands: int


# ── Data Export/Import ─────────────────────────────


class DataExport(BaseModel):
    nodes: list[NodeResponse]
    rules: list[RuleResponse]
    settings: SettingsResponse
