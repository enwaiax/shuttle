import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import {
  ScrollText,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  RefreshCw,
} from "lucide-react";
import { useLogs, useStats } from "../api/client";
import type { CommandLogResponse } from "../api/client";
import Badge from "../components/Badge";
import EmptyState from "../components/EmptyState";

const PAGE_SIZE = 50;

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function LogRow({ log }: { log: CommandLogResponse }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className="cursor-pointer transition-colors hover:bg-gray-50/60"
      >
        <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-500">
          {formatTimestamp(log.executed_at)}
        </td>
        <td className="max-w-md truncate px-4 py-3">
          <code className="text-xs text-gray-800">{log.command}</code>
        </td>
        <td className="whitespace-nowrap px-4 py-3 text-sm">
          {log.exit_code === 0 ? (
            <CheckCircle2 size={16} className="text-green-500" />
          ) : log.exit_code != null ? (
            <span className="flex items-center gap-1 text-red-500">
              <XCircle size={16} />
              <span className="text-xs">{log.exit_code}</span>
            </span>
          ) : (
            <span className="text-xs text-gray-400">--</span>
          )}
        </td>
        <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-500">
          {log.duration_ms != null ? `${log.duration_ms}ms` : "--"}
        </td>
        <td className="whitespace-nowrap px-4 py-3">
          {log.security_level ? <Badge value={log.security_level} /> : "--"}
        </td>
        <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-400">
          {log.node_name ?? "--"}
        </td>
      </tr>
      {expanded && (log.stdout || log.stderr) && (
        <tr>
          <td colSpan={6} className="bg-gray-50 px-6 py-4">
            {log.stdout && (
              <div className="mb-2">
                <p className="mb-1 text-xs font-medium text-gray-500">stdout</p>
                <pre className="max-h-48 overflow-auto rounded-lg bg-white p-3 text-xs text-gray-700 ring-1 ring-gray-200">
                  {log.stdout}
                </pre>
              </div>
            )}
            {log.stderr && (
              <div>
                <p className="mb-1 text-xs font-medium text-red-500">stderr</p>
                <pre className="max-h-48 overflow-auto rounded-lg bg-white p-3 text-xs text-red-600 ring-1 ring-red-200">
                  {log.stderr}
                </pre>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export default function Activity() {
  const { nodeId } = useParams<{ nodeId?: string }>();
  const [page, setPage] = useState(1);
  const [autoRefresh, setAutoRefresh] = useState(false);

  // Reset page when node changes
  useEffect(() => {
    setPage(1);
  }, [nodeId]);

  const { data, refetch } = useLogs({
    node_id: nodeId,
    page,
    page_size: PAGE_SIZE,
  });
  const { data: stats } = useStats();

  const doRefetch = useCallback(() => {
    void refetch();
  }, [refetch]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(doRefetch, 5000);
    return () => clearInterval(id);
  }, [autoRefresh, doRefetch]);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Activity</h1>
          <p className="mt-1 text-sm text-gray-500">
            {nodeId ? "Commands for this node" : "All command activity across nodes"}
          </p>
        </div>
        <button
          onClick={() => setAutoRefresh((v) => !v)}
          className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium shadow-sm transition-colors ${
            autoRefresh
              ? "border-blue-300 bg-blue-50 text-blue-700"
              : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
          }`}
        >
          <RefreshCw size={13} className={autoRefresh ? "animate-spin" : ""} />
          {autoRefresh ? "Live" : "Auto-refresh"}
        </button>
      </div>

      {/* Stats bar */}
      {stats && (
        <div className="mt-4 grid grid-cols-3 gap-4">
          {[
            { label: "Nodes", value: stats.node_count },
            { label: "Active Sessions", value: stats.active_sessions },
            { label: "Total Commands", value: stats.total_commands },
          ].map((s) => (
            <div
              key={s.label}
              className="rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm"
            >
              <p className="text-xs font-medium text-gray-500">{s.label}</p>
              <p className="mt-1 text-xl font-semibold text-gray-900">
                {s.value.toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Log table */}
      <div className="mt-6">
        {items.length === 0 && page === 1 ? (
          <EmptyState
            icon={ScrollText}
            title="No activity yet"
            description={
              nodeId
                ? "No commands have been executed on this node."
                : "Command execution logs will appear here."
            }
          />
        ) : (
          <>
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr className="bg-gray-50/80">
                    {["Time", "Command", "Exit", "Duration", "Level", "Node"].map(
                      (h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {items.map((log) => (
                    <LogRow key={log.id} log={log} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Page {page} of {totalPages} ({total} total)
              </p>
              <div className="flex gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="inline-flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-40"
                >
                  <ChevronLeft size={14} />
                  Previous
                </button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="inline-flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-40"
                >
                  Next
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
