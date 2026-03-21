import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import type {
  NodeResponse,
  NodeCreate,
  NodeUpdate,
  RuleResponse,
  RuleCreate,
  RuleUpdate,
  SessionResponse,
  CommandLogResponse,
  LogListResponse,
  StatsResponse,
  SettingsResponse,
  SettingsUpdate,
} from "../types";

// ── Fetch wrapper ──────────────────────────────────

const BASE = "/api";

export function getToken(): string | null {
  return localStorage.getItem("shuttle_token");
}

export function setToken(token: string) {
  localStorage.setItem("shuttle_token", token);
}

export function clearToken() {
  localStorage.removeItem("shuttle_token");
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...init?.headers as Record<string, string>,
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (res.status === 401) {
    clearToken();
    window.location.reload();
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Query keys ─────────────────────────────────────

const keys = {
  stats: ["stats"] as const,
  nodes: (tag?: string) =>
    tag ? (["nodes", tag] as const) : (["nodes"] as const),
  node: (id: string) => ["nodes", id] as const,
  rules: ["rules"] as const,
  sessions: (status?: string) =>
    status ? (["sessions", status] as const) : (["sessions"] as const),
  logs: (params?: LogParams) => ["logs", params] as const,
  settings: ["settings"] as const,
};

// ── Stats ──────────────────────────────────────────

export function useStats() {
  return useQuery<StatsResponse>({
    queryKey: keys.stats,
    queryFn: () => apiFetch("/stats"),
  });
}

// ── Nodes ──────────────────────────────────────────

export function useNodes(tag?: string) {
  return useQuery<NodeResponse[]>({
    queryKey: keys.nodes(tag),
    queryFn: () =>
      apiFetch(`/nodes${tag ? `?tag=${encodeURIComponent(tag)}` : ""}`),
  });
}

export function useNode(id: string) {
  return useQuery<NodeResponse>({
    queryKey: keys.node(id),
    queryFn: () => apiFetch(`/nodes/${id}`),
    enabled: !!id,
  });
}

export function useCreateNode() {
  const qc = useQueryClient();
  return useMutation<NodeResponse, Error, NodeCreate>({
    mutationFn: (body) =>
      apiFetch("/nodes", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["nodes"] });
      void qc.invalidateQueries({ queryKey: keys.stats });
    },
  });
}

export function useUpdateNode(id: string) {
  const qc = useQueryClient();
  return useMutation<NodeResponse, Error, NodeUpdate>({
    mutationFn: (body) =>
      apiFetch(`/nodes/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["nodes"] });
    },
  });
}

export interface TestNodeResult {
  success: boolean;
  message: string;
}

export function useTestNode() {
  return useMutation<TestNodeResult, Error, string>({
    mutationFn: (id) =>
      apiFetch(`/nodes/${id}/test`, { method: "POST" }),
  });
}

export function useDeleteNode() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => apiFetch(`/nodes/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["nodes"] });
      void qc.invalidateQueries({ queryKey: keys.stats });
    },
  });
}

// ── Rules ──────────────────────────────────────────

export function useRules() {
  return useQuery<RuleResponse[]>({
    queryKey: keys.rules,
    queryFn: () => apiFetch("/rules"),
  });
}

export function useCreateRule() {
  const qc = useQueryClient();
  return useMutation<RuleResponse, Error, RuleCreate>({
    mutationFn: (body) =>
      apiFetch("/rules", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.rules });
    },
  });
}

export function useUpdateRule(id: string) {
  const qc = useQueryClient();
  return useMutation<RuleResponse, Error, RuleUpdate>({
    mutationFn: (body) =>
      apiFetch(`/rules/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.rules });
    },
  });
}

export function useDeleteRule() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id) => apiFetch(`/rules/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.rules });
    },
  });
}

export function useReorderRules() {
  const qc = useQueryClient();
  return useMutation<RuleResponse[], Error, string[]>({
    mutationFn: (ids) =>
      apiFetch("/rules/reorder", {
        method: "POST",
        body: JSON.stringify({ ids }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.rules });
    },
  });
}

// ── Sessions ───────────────────────────────────────

export function useSessions(status?: string) {
  return useQuery<SessionResponse[]>({
    queryKey: keys.sessions(status),
    queryFn: () =>
      apiFetch(
        `/sessions${status ? `?status_filter=${encodeURIComponent(status)}` : ""}`,
      ),
  });
}

export function useCloseSession() {
  const qc = useQueryClient();
  return useMutation<SessionResponse, Error, string>({
    mutationFn: (id) => apiFetch(`/sessions/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["sessions"] });
      void qc.invalidateQueries({ queryKey: keys.stats });
    },
  });
}

// ── Logs ───────────────────────────────────────────

export interface LogParams {
  page?: number;
  page_size?: number;
  node_id?: string;
  session_id?: string;
  since?: string;
  until?: string;
}

export function useLogs(params?: LogParams) {
  return useQuery<LogListResponse>({
    queryKey: keys.logs(params),
    queryFn: () => {
      const search = new URLSearchParams();
      if (params?.page) search.set("page", String(params.page));
      if (params?.page_size) search.set("page_size", String(params.page_size));
      if (params?.node_id) search.set("node_id", params.node_id);
      if (params?.session_id) search.set("session_id", params.session_id);
      if (params?.since) search.set("since", params.since);
      if (params?.until) search.set("until", params.until);
      const qs = search.toString();
      return apiFetch(`/logs${qs ? `?${qs}` : ""}`);
    },
  });
}

// ── Data Export / Import ──────────────────────────

export async function exportData(): Promise<Blob> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}/data/export`, { method: "POST", headers });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.blob();
}

export async function importData(data: unknown): Promise<{ message: string }> {
  return apiFetch("/data/import", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ── Settings ───────────────────────────────────────

export function useSettings() {
  return useQuery<SettingsResponse>({
    queryKey: keys.settings,
    queryFn: () => apiFetch("/settings"),
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation<SettingsResponse, Error, SettingsUpdate>({
    mutationFn: (body) =>
      apiFetch("/settings", { method: "PUT", body: JSON.stringify(body) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.settings });
    },
  });
}

// ── Effective Rules ────────────────────────────────

export function useEffectiveRules(nodeId: string) {
  return useQuery<RuleResponse[]>({
    queryKey: ["rules", "effective", nodeId],
    queryFn: () => apiFetch(`/rules/effective/${nodeId}`),
    enabled: !!nodeId,
  });
}

// Re-export types for convenience
export type { CommandLogResponse };
