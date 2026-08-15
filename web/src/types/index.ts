// ── Nodes ──────────────────────────────────────────

export interface NodeResponse {
  id: string;
  name: string;
  host: string;
  port: number;
  username: string;
  auth_type: string;
  jump_host_id: string | null;
  tags: string[] | null;
  status: string;
  latency_ms: number | null;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface NodeCreate {
  name: string;
  host: string;
  port?: number;
  username: string;
  auth_type?: string;
  credential: string;
  jump_host_id?: string | null;
  tags?: string[] | null;
}

export interface NodeUpdate {
  name?: string | null;
  host?: string | null;
  port?: number | null;
  username?: string | null;
  auth_type?: string | null;
  credential?: string | null;
  jump_host_id?: string | null;
  tags?: string[] | null;
}

// ── Security Rules ─────────────────────────────────

export interface RuleResponse {
  id: string;
  pattern: string;
  level: string;
  node_id: string | null;
  description: string | null;
  priority: number;
  enabled: boolean;
  created_at: string;
}

export interface RuleCreate {
  pattern: string;
  level: string;
  node_id?: string | null;
  description?: string | null;
  priority?: number;
  enabled?: boolean;
}

export interface RuleUpdate {
  pattern?: string;
  level?: string;
  node_id?: string | null;
  description?: string | null;
  priority?: number;
  enabled?: boolean;
}

// ── Sessions ───────────────────────────────────────

export interface SessionResponse {
  id: string;
  node_id: string;
  node_name: string | null;
  working_directory: string | null;
  status: string;
  created_at: string;
  closed_at: string | null;
}

// ── Command Logs ───────────────────────────────────

export interface CommandLogResponse {
  id: string;
  session_id: string | null;
  node_id: string;
  node_name: string | null;
  command: string;
  action: string;
  actor_id: string;
  client_id: string;
  conversation_id: string;
  approval_id: string | null;
  exit_code: number | null;
  stdout: string | null;
  stderr: string | null;
  security_level: string | null;
  bypassed: boolean;
  duration_ms: number | null;
  executed_at: string;
}

export interface LogListResponse {
  items: CommandLogResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApprovalResponse {
  id: string;
  node_id: string;
  node_name: string;
  action: string;
  command: string;
  actor_id: string;
  client_id: string;
  conversation_id: string;
  rule_id: string | null;
  reason: string | null;
  status: "pending" | "approved" | "denied" | "consumed" | "expired";
  approver: string | null;
  decision_reason: string | null;
  created_at: string;
  expires_at: string;
  decided_at: string | null;
  consumed_at: string | null;
}

// ── Settings ───────────────────────────────────────

export interface SettingsResponse {
  pool_max_total: number;
  pool_max_per_node: number;
  pool_idle_timeout: number;
  pool_max_lifetime: number;
  pool_queue_size: number;
  cleanup_command_logs_days: number;
  cleanup_closed_sessions_days: number;
}

export interface SettingsUpdate {
  pool_max_total?: number;
  pool_max_per_node?: number;
  pool_idle_timeout?: number;
  pool_max_lifetime?: number;
  pool_queue_size?: number;
  cleanup_command_logs_days?: number;
  cleanup_closed_sessions_days?: number;
}

// ── Stats ──────────────────────────────────────────

export interface StatsResponse {
  node_count: number;
  active_sessions: number;
  total_commands: number;
}
