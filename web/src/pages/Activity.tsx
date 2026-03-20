import { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import { RefreshCw, ChevronUp, Terminal } from "lucide-react";
import { useLogs, useStats } from "../api/client";
import type { CommandLogResponse } from "../api/client";
import EmptyState from "../components/EmptyState";

const PAGE_SIZE = 100;

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatDuration(ms: number | null): string {
  if (ms == null) return "";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m${Math.floor((ms % 60000) / 1000)}s`;
}

function securityColor(level: string | null): string {
  if (!level) return "";
  switch (level) {
    case "block":
      return "text-red-400";
    case "confirm":
      return "text-amber-400";
    case "warn":
      return "text-yellow-400";
    default:
      return "";
  }
}

function exitIndicator(code: number | null): { symbol: string; cls: string } {
  if (code === null) return { symbol: "…", cls: "text-zinc-500" };
  if (code === 0) return { symbol: "✓", cls: "text-emerald-400" };
  return { symbol: `✗ ${code}`, cls: "text-red-400" };
}

function LogEntry({ log }: { log: CommandLogResponse }) {
  const [expanded, setExpanded] = useState(false);
  const exit = exitIndicator(log.exit_code);
  const secCls = securityColor(log.security_level);
  const hasOutput = !!(log.stdout || log.stderr);

  return (
    <div className="group border-b border-zinc-800/60 last:border-0">
      {/* Command line */}
      <div
        onClick={() => hasOutput && setExpanded(!expanded)}
        className={`flex items-start gap-0 px-4 py-1.5 font-mono text-[13px] leading-relaxed ${
          hasOutput ? "cursor-pointer hover:bg-zinc-800/40" : ""
        } transition-colors`}
      >
        {/* Timestamp */}
        <span className="w-20 shrink-0 text-zinc-500">{formatTime(log.executed_at)}</span>

        {/* Node name */}
        {log.node_name && (
          <span className="w-28 shrink-0 truncate text-cyan-500/70">{log.node_name}</span>
        )}

        {/* Prompt + command */}
        <span className="mr-1.5 text-zinc-500">$</span>
        <span className="flex-1 text-zinc-200">{log.command}</span>

        {/* Security badge */}
        {log.security_level && log.security_level !== "allow" && (
          <span className={`mx-2 shrink-0 text-xs ${secCls}`}>
            {log.security_level}
          </span>
        )}

        {/* Exit + duration */}
        <span className={`w-12 shrink-0 text-right ${exit.cls}`}>{exit.symbol}</span>
        <span className="w-16 shrink-0 text-right text-zinc-600">
          {formatDuration(log.duration_ms)}
        </span>

        {/* Expand indicator */}
        {hasOutput && (
          <ChevronUp
            size={12}
            className={`ml-1 shrink-0 text-zinc-600 transition-transform ${
              expanded ? "" : "rotate-180"
            }`}
          />
        )}
      </div>

      {/* Expanded output */}
      {expanded && (
        <div className="mx-4 mb-2 mt-0.5 rounded-md bg-zinc-950/60 px-4 py-3">
          {log.stdout && (
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap text-[12px] leading-relaxed text-zinc-400">
              {log.stdout}
            </pre>
          )}
          {log.stderr && (
            <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap text-[12px] leading-relaxed text-red-400/80">
              {log.stderr}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

export default function Activity() {
  const { nodeId } = useParams<{ nodeId?: string }>();
  const [page, setPage] = useState(1);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

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
  const hasMore = total > page * PAGE_SIZE;

  return (
    <div className="flex h-full flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-zinc-800/60 bg-zinc-900/80 px-4 py-2.5">
        <div className="flex items-center gap-3">
          <Terminal size={14} className="text-zinc-500" />
          <span className="text-sm font-medium text-zinc-300">
            {nodeId ? `Node Activity` : "All Activity"}
          </span>
          {stats && (
            <span className="text-xs text-zinc-600">
              {stats.node_count} nodes · {stats.active_sessions} sessions · {total} commands
            </span>
          )}
        </div>
        <button
          onClick={() => setAutoRefresh((v) => !v)}
          className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            autoRefresh
              ? "bg-emerald-500/10 text-emerald-400"
              : "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
          }`}
        >
          <RefreshCw size={11} className={autoRefresh ? "animate-spin" : ""} />
          {autoRefresh ? "Live" : "Auto"}
        </button>
      </div>

      {/* Console output */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto bg-zinc-900 font-mono"
      >
        {items.length === 0 && page === 1 ? (
          <div className="flex h-full items-center justify-center">
            <EmptyState
              icon={Terminal}
              title="No activity yet"
              description={
                nodeId
                  ? "No commands have been executed on this node."
                  : "Command execution logs will appear here."
              }
            />
          </div>
        ) : (
          <>
            {items.map((log) => (
              <LogEntry key={log.id} log={log} />
            ))}

            {/* Load more / pagination */}
            <div className="flex items-center justify-center gap-4 px-4 py-3">
              {page > 1 && (
                <button
                  onClick={() => setPage((p) => p - 1)}
                  className="text-xs text-zinc-500 hover:text-zinc-300"
                >
                  ↑ Newer
                </button>
              )}
              <span className="text-xs text-zinc-600">
                {total} commands{hasMore ? ` · page ${page}` : ""}
              </span>
              {hasMore && (
                <button
                  onClick={() => setPage((p) => p + 1)}
                  className="text-xs text-zinc-500 hover:text-zinc-300"
                >
                  ↓ Older
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
