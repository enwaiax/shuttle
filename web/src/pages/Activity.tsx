import { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import { RefreshCw, Download, Terminal } from "lucide-react";
import { useLogs, useNode } from "../api/client";
import type { CommandLogResponse } from "../api/client";
import EmptyState from "../components/EmptyState";

const PAGE_SIZE = 50;
const OUTPUT_PREVIEW_LINES = 15;

// ── Helpers ──────────────────────────────────────────

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

function truncateOutput(text: string): { preview: string; isTruncated: boolean } {
  const lines = text.split("\n");
  if (lines.length <= OUTPUT_PREVIEW_LINES) return { preview: text, isTruncated: false };
  return { preview: lines.slice(0, OUTPUT_PREVIEW_LINES).join("\n"), isTruncated: true };
}

type TimeRange = "today" | "7d" | "30d" | "all";

// ── Single command entry ────────────────────────────

function CommandEntry({ log }: { log: CommandLogResponse }) {
  const [showFull, setShowFull] = useState(false);

  const hasFailed = log.exit_code !== null && log.exit_code !== 0;
  const secLevel = log.security_level;
  const hasSecEvent = secLevel && secLevel !== "allow";

  const stdout = log.stdout || "";
  const stderr = log.stderr || "";
  const { preview: stdoutPreview, isTruncated: stdoutTruncated } = truncateOutput(stdout);
  const { preview: stderrPreview, isTruncated: stderrTruncated } = truncateOutput(stderr);
  const isTruncated = stdoutTruncated || stderrTruncated;

  return (
    <div
      className={`border-l-2 py-1.5 pl-4 pr-4 ${
        hasFailed
          ? "border-l-red-500/60"
          : hasSecEvent
            ? "border-l-amber-500/40"
            : "border-l-transparent"
      }`}
    >
      {/* Command line */}
      <div className="flex items-baseline gap-0 font-mono text-[13px] leading-relaxed">
        <span className="mr-3 shrink-0 text-zinc-600">{formatTime(log.executed_at)}</span>
        <span className="mr-1.5 text-zinc-500">$</span>
        <span className="flex-1 text-zinc-200">{log.command}</span>

        {hasSecEvent && (
          <span
            className={`mx-2 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${
              secLevel === "block"
                ? "bg-red-500/15 text-red-400"
                : secLevel === "confirm"
                  ? "bg-amber-500/15 text-amber-400"
                  : "bg-yellow-500/10 text-yellow-400"
            }`}
          >
            {secLevel}
          </span>
        )}

        <span
          className={`ml-2 shrink-0 text-xs ${
            hasFailed ? "text-red-400" : log.exit_code === 0 ? "text-emerald-500/70" : "text-zinc-600"
          }`}
        >
          {log.exit_code !== null ? (log.exit_code === 0 ? "✓" : `✗ ${log.exit_code}`) : "…"}
        </span>
        {log.duration_ms != null && (
          <span className="ml-2 shrink-0 text-xs text-zinc-600">
            {formatDuration(log.duration_ms)}
          </span>
        )}
      </div>

      {/* Output — shown by default */}
      {(stdout || stderr) && (
        <div className="ml-16 mt-1">
          {stdout && (
            <pre className="whitespace-pre-wrap text-[12px] leading-relaxed text-zinc-500">
              {showFull ? stdout : stdoutPreview}
            </pre>
          )}
          {stderr && (
            <pre className="mt-1 whitespace-pre-wrap text-[12px] leading-relaxed text-red-400/70">
              {showFull ? stderr : stderrPreview}
            </pre>
          )}
          {isTruncated && !showFull && (
            <button
              onClick={() => setShowFull(true)}
              className="mt-1 text-[11px] text-zinc-600 hover:text-zinc-400"
            >
              ▸ Show full output ({stdout.split("\n").length + stderr.split("\n").length} lines)
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main view ───────────────────────────────────────

export default function Activity() {
  const { nodeId } = useParams<{ nodeId?: string }>();
  const [timeRange, setTimeRange] = useState<TimeRange>("today");
  const [page, setPage] = useState(1);
  const [allItems, setAllItems] = useState<CommandLogResponse[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: node } = useNode(nodeId ?? "");

  useEffect(() => {
    setPage(1);
    setAllItems([]);
  }, [nodeId, timeRange]);

  const { data, refetch, isFetching } = useLogs({
    node_id: nodeId,
    page,
    page_size: PAGE_SIZE,
  });

  // Accumulate pages for infinite scroll
  useEffect(() => {
    if (data?.items) {
      if (page === 1) {
        setAllItems(data.items);
      } else {
        setAllItems((prev) => {
          const ids = new Set(prev.map((i) => i.id));
          return [...prev, ...data.items.filter((i) => !ids.has(i.id))];
        });
      }
    }
  }, [data, page]);

  const doRefetch = useCallback(() => void refetch(), [refetch]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(doRefetch, 5000);
    return () => clearInterval(id);
  }, [autoRefresh, doRefetch]);

  // Infinite scroll
  useEffect(() => {
    const el = bottomRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && data && allItems.length < data.total && !isFetching) {
          setPage((p) => p + 1);
        }
      },
      { threshold: 0.1 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [data, allItems.length, isFetching]);

  const total = data?.total ?? 0;
  const exportUrl = `/api/logs/export?format=csv${nodeId ? `&node_id=${nodeId}` : ""}`;

  const ranges: { label: string; value: TimeRange }[] = [
    { label: "Today", value: "today" },
    { label: "7d", value: "7d" },
    { label: "30d", value: "30d" },
    { label: "All", value: "all" },
  ];

  // No node selected yet (sidebar will auto-redirect)
  if (!nodeId) {
    return (
      <div className="flex h-full items-center justify-center bg-zinc-900">
        <p className="text-sm text-zinc-600">Select a node from the sidebar</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-zinc-800/60 bg-zinc-900/90 px-4 py-2">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-zinc-300">
            {node?.name ?? "…"}
          </span>
          <span className="text-[11px] text-zinc-600">
            {node ? `${node.host}:${node.port}` : ""}
          </span>

          {/* Time range */}
          <div className="flex items-center gap-0.5 rounded-md bg-zinc-800/60 p-0.5">
            {ranges.map((r) => (
              <button
                key={r.value}
                onClick={() => setTimeRange(r.value)}
                className={`rounded px-2 py-0.5 text-[11px] font-medium transition-colors ${
                  timeRange === r.value
                    ? "bg-zinc-700 text-zinc-200"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>

          <span className="text-[11px] text-zinc-600">{total} commands</span>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={exportUrl}
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
          >
            <Download size={11} />
            CSV
          </a>
          <button
            onClick={() => setAutoRefresh((v) => !v)}
            className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
              autoRefresh
                ? "bg-emerald-500/10 text-emerald-400"
                : "text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
            }`}
          >
            <RefreshCw size={11} className={autoRefresh ? "animate-spin" : ""} />
            {autoRefresh ? "Live" : "Auto"}
          </button>
        </div>
      </div>

      {/* Console */}
      <div className="flex-1 overflow-y-auto bg-zinc-900">
        {allItems.length === 0 && !isFetching ? (
          <div className="flex h-full items-center justify-center">
            <EmptyState
              icon={Terminal}
              title="No commands yet"
              description="Commands executed on this node will appear here."
            />
          </div>
        ) : (
          <div className="divide-y divide-zinc-800/40 py-1">
            {allItems.map((log) => (
              <CommandEntry key={log.id} log={log} />
            ))}
            <div ref={bottomRef} className="h-4" />
            {isFetching && (
              <div className="py-3 text-center text-xs text-zinc-600">Loading…</div>
            )}
            {!isFetching && allItems.length >= total && total > 0 && (
              <div className="py-3 text-center text-xs text-zinc-700">
                — {total} commands —
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
