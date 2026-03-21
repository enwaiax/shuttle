import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Server, Terminal, Plus, Activity, Cpu, Pencil, Plug, Loader2, CheckCircle2, XCircle, Trash2 } from "lucide-react";

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
import { toast } from "sonner";
import { useNodes, useStats, useLogs, useTestNode, useDeleteNode } from "../api/client";
import type { NodeResponse } from "../types";
import type { CommandLogResponse } from "../api/client";
import { StatCardSkeleton, NodeCardSkeleton } from "../components/Skeleton";
import NodeForm from "./NodeForm";
import clsx from "clsx";

function StatCard({
  label,
  value,
  icon: Icon,
  delay,
}: {
  label: string;
  value: number | undefined;
  icon: typeof Server;
  delay: string;
}) {
  return (
    <div
      className="animate-slide-up group rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-5 transition-all duration-300 hover:border-[var(--green)]/20 hover:shadow-[0_0_30px_rgba(118,185,0,0.05)]"
      style={{ animationDelay: delay }}
    >
      <div className="flex items-center justify-between">
        <p className="text-[12px] font-medium text-[var(--text-tertiary)]">{label}</p>
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--green-subtle)]">
          <Icon size={15} className="text-[var(--green)]" strokeWidth={1.8} />
        </div>
      </div>
      <p className="mt-3 text-[28px] font-bold tabular-nums tracking-[-0.04em] text-[var(--text-primary)]">
        {value !== undefined ? value.toLocaleString() : "\u2014"}
      </p>
    </div>
  );
}

function NodeCardTestButton({ nodeId, onLatency }: { nodeId: string; onLatency?: (ms: number | null) => void }) {
  const testNode = useTestNode();
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  function handleTest(e: React.MouseEvent) {
    e.stopPropagation();
    setResult(null);
    testNode.mutate(nodeId, {
      onSuccess: (data) => {
        setResult(data);
        // Try to extract latency from message like "Connection successful (12ms)"
        const match = data.message?.match(/\((\d+)ms\)/);
        if (match && onLatency) onLatency(Number(match[1]));
        setTimeout(() => setResult(null), 5000);
      },
      onError: (err) => {
        setResult({ success: false, message: err.message });
        if (onLatency) onLatency(null);
        setTimeout(() => setResult(null), 5000);
      },
    });
  }

  return (
    <button
      onClick={handleTest}
      disabled={testNode.isPending}
      title={result ? result.message : "Test connection"}
      className="rounded-lg p-1.5 text-[var(--text-quaternary)] transition-colors hover:bg-[var(--green-subtle)] hover:text-[var(--green)] disabled:opacity-50"
    >
      {testNode.isPending ? (
        <Loader2 size={13} className="animate-spin" />
      ) : result ? (
        result.success ? (
          <CheckCircle2 size={13} className="text-[var(--green)]" />
        ) : (
          <XCircle size={13} className="text-[var(--red)]" />
        )
      ) : (
        <Plug size={13} strokeWidth={1.5} />
      )}
    </button>
  );
}

function NodeCard({
  node,
  onClick,
  onEdit,
  onDelete,
  index,
}: {
  node: NodeResponse;
  onClick: () => void;
  onEdit: () => void;
  onDelete: () => void;
  index: number;
}) {
  const isOffline = node.status === "offline";
  const [latencyMs, setLatencyMs] = useState<number | null>(node.latency_ms);

  // Format "last seen" as relative time
  const lastSeen = node.last_seen_at
    ? formatTimeAgo(new Date(node.last_seen_at))
    : null;

  return (
    <div
      className="animate-slide-up group flex flex-col rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-5 text-left transition-all duration-300 hover:border-[var(--border-strong)] hover:bg-[var(--bg-tertiary)]"
      style={{ animationDelay: `${0.1 + index * 0.05}s` }}
    >
      <div className="flex items-center gap-3">
        <span
          className={clsx(
            "h-2 w-2 rounded-full",
            isOffline ? "bg-[var(--red)]" : latencyMs != null ? "bg-[var(--green)] animate-pulse-green" : "bg-[var(--text-quaternary)]",
          )}
        />
        <span className="text-[14px] font-semibold text-[var(--text-primary)]">
          {node.name}
        </span>
        {isOffline ? (
          <span className="text-[10px] font-medium text-[var(--red)]">unreachable</span>
        ) : latencyMs != null ? (
          <span className="text-[10px] tabular-nums font-medium text-[var(--green)]" style={{ fontFamily: "var(--font-mono)" }}>
            {latencyMs}ms
          </span>
        ) : null}
        <div className="ml-auto flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
          <NodeCardTestButton nodeId={node.id} onLatency={setLatencyMs} />
          <button
            onClick={(e) => { e.stopPropagation(); onEdit(); }}
            title="Edit node"
            className="rounded-lg p-1.5 text-[var(--text-quaternary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
          >
            <Pencil size={13} strokeWidth={1.5} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            title="Delete node"
            className="rounded-lg p-1.5 text-[var(--text-quaternary)] transition-colors hover:bg-[var(--red)]/10 hover:text-[var(--red)]"
          >
            <Trash2 size={13} strokeWidth={1.5} />
          </button>
        </div>
      </div>
      <p
        className="mt-3 text-[12px] text-[var(--text-quaternary)]"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {node.username}@{node.host}:{node.port}
        {lastSeen && <span className="text-[var(--text-muted)]"> · {lastSeen}</span>}
      </p>
      {node.tags && node.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {node.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-md bg-[var(--bg-elevated)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-tertiary)]"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
      <button
        onClick={onClick}
        className="mt-4 flex items-center gap-1.5 text-[11px] text-[var(--text-muted)] transition-colors group-hover:text-[var(--green)]"
      >
        <Terminal size={11} strokeWidth={1.5} />
        <span>View activity</span>
        <span className="ml-auto opacity-0 transition-opacity group-hover:opacity-100">&rarr;</span>
      </button>
    </div>
  );
}

function RecentCommandEntry({ log, onClick }: { log: CommandLogResponse; onClick: () => void }) {
  const failed = log.exit_code !== null && log.exit_code !== 0;
  const time = new Date(log.executed_at).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-lg px-4 py-2.5 text-left transition-colors hover:bg-[var(--bg-hover)]"
    >
      <span
        className={clsx(
          "h-[6px] w-[6px] shrink-0 rounded-full",
          failed ? "bg-[var(--red)]" : "bg-[var(--green)]",
        )}
      />
      <span className="w-[52px] shrink-0 text-[11px] tabular-nums text-[var(--text-quaternary)]" style={{ fontFamily: "var(--font-mono)" }}>
        {time}
      </span>
      {log.node_name && (
        <span className="shrink-0 rounded bg-[var(--bg-elevated)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-tertiary)]">
          {log.node_name}
        </span>
      )}
      <span
        className={clsx(
          "min-w-0 flex-1 truncate text-[12px]",
          failed ? "text-[var(--red)]" : "text-[var(--text-secondary)]",
        )}
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {log.command}
      </span>
      <span
        className={clsx(
          "shrink-0 text-[10px] tabular-nums",
          failed ? "text-[var(--red)]" : log.exit_code === 0 ? "text-[var(--green)]" : "text-[var(--text-muted)]",
        )}
      >
        {log.exit_code !== null ? String(log.exit_code) : "\u00B7"}
      </span>
    </button>
  );
}

export default function Overview() {
  const { data: nodes, isLoading: nodesLoading } = useNodes();
  const { data: stats, isLoading: statsLoading } = useStats();
  const { data: recentLogs } = useLogs({ page: 1, page_size: 8 });
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);
  const [editNodeId, setEditNodeId] = useState<string | null>(null);
  const deleteNode = useDeleteNode();

  const nodeList = nodes ?? [];

  function openEditForm(nodeId: string) {
    setEditNodeId(nodeId);
    setShowForm(true);
  }

  function handleDelete(node: NodeResponse) {
    if (!confirm(`Delete node "${node.name}"? This cannot be undone.`)) return;
    deleteNode.mutate(node.id, {
      onSuccess: () => toast.success(`Node "${node.name}" deleted`),
      onError: (err) => toast.error(`Failed to delete: ${err.message}`),
    });
  }

  function handleFormClose(open: boolean) {
    setShowForm(open);
    if (!open) setEditNodeId(null);
  }

  return (
    <div className="flex h-full flex-col bg-[var(--bg-primary)]">
      {/* Header */}
      <div className="border-b border-[var(--border-subtle)] px-8 py-7">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--green-subtle)]">
            <Server size={15} className="text-[var(--green)]" strokeWidth={1.8} />
          </div>
          <div>
            <h1 className="text-[17px] font-bold tracking-[-0.02em] text-[var(--text-primary)]">
              Nodes
            </h1>
            <p className="text-[12px] text-[var(--text-tertiary)]">
              {stats
                ? `${stats.node_count} nodes connected \u00B7 ${stats.total_commands.toLocaleString()} commands executed`
                : "Loading\u2026"}
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-8 py-7">
        {/* Stats row */}
        {statsLoading ? (
          <div className="grid grid-cols-3 gap-4">
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Total Nodes" value={stats?.node_count} icon={Cpu} delay="0s" />
            <StatCard label="Active Sessions" value={stats?.active_sessions} icon={Activity} delay="0.05s" />
            <StatCard label="Commands Executed" value={stats?.total_commands} icon={Terminal} delay="0.1s" />
          </div>
        )}

        {/* Recent Commands */}
        {recentLogs && recentLogs.items.length > 0 && (
          <div className="animate-fade-in mt-8">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[var(--text-quaternary)]">
                Recent Commands
              </p>
              <span className="text-[10px] tabular-nums text-[var(--text-muted)]">
                {recentLogs.total.toLocaleString()} total
              </span>
            </div>
            <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
              {recentLogs.items.map((log) => (
                <RecentCommandEntry
                  key={log.id}
                  log={log}
                  onClick={() => navigate(`/nodes/${log.node_id}`)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Node grid */}
        <div className="mt-8">
          {nodesLoading ? (
            <>
              <p className="mb-4 text-[11px] font-semibold uppercase tracking-[0.1em] text-[var(--text-quaternary)]">
                Nodes
              </p>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <NodeCardSkeleton />
                <NodeCardSkeleton />
                <NodeCardSkeleton />
              </div>
            </>
          ) : nodeList.length === 0 ? (
            <div className="animate-fade-in flex flex-col items-center justify-center py-20">
              <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--border-default)] bg-[var(--bg-elevated)]">
                <Server size={24} className="text-[var(--text-quaternary)]" strokeWidth={1.5} />
              </div>
              <p className="text-[15px] font-semibold text-[var(--text-primary)]">
                No nodes configured
              </p>
              <p className="mt-2 text-[13px] text-[var(--text-tertiary)]">
                Add a node to start monitoring SSH activity
              </p>
              <button
                onClick={() => { setEditNodeId(null); setShowForm(true); }}
                className="mt-5 rounded-xl bg-[var(--green)] px-5 py-2.5 text-[13px] font-semibold text-black transition-all duration-200 hover:bg-[var(--green-light)] hover:shadow-[0_0_24px_rgba(118,185,0,0.3)]"
              >
                Add Node
              </button>
            </div>
          ) : (
            <>
              <div className="mb-4 flex items-center justify-between">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[var(--text-quaternary)]">
                  Nodes
                </p>
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {nodeList.map((node, i) => (
                  <NodeCard
                    key={node.id}
                    node={node}
                    onClick={() => navigate(`/nodes/${node.id}`)}
                    onEdit={() => openEditForm(node.id)}
                    onDelete={() => handleDelete(node)}
                    index={i}
                  />
                ))}
                <button
                  onClick={() => { setEditNodeId(null); setShowForm(true); }}
                  aria-label="Add new node"
                  className="animate-slide-up flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border-default)] p-5 text-[var(--text-quaternary)] transition-all duration-300 hover:border-[var(--green)]/30 hover:text-[var(--green)]"
                  style={{ animationDelay: `${0.1 + nodeList.length * 0.05}s` }}
                >
                  <Plus size={18} strokeWidth={1.5} />
                  <span className="mt-2 text-[12px] font-medium">Add node</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <NodeForm open={showForm} onOpenChange={handleFormClose} nodeId={editNodeId} />
    </div>
  );
}
