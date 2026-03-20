import { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import { RefreshCw, Download, Terminal, ChevronRight } from "lucide-react";
import { useLogs, useNode } from "../api/client";
import type { CommandLogResponse } from "../api/client";
import clsx from "clsx";

const PAGE_SIZE = 50;
const PREVIEW_LINES = 15;

// ── Helpers ─────────────────────────────────────────

const mono = { fontFamily: "'JetBrains Mono', 'Fira Code', monospace" };

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function fmtDuration(ms: number | null): string {
  if (ms == null) return "";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60_000)}m${Math.floor((ms % 60_000) / 1000)}s`;
}

function truncate(text: string) {
  const lines = text.split("\n");
  if (lines.length <= PREVIEW_LINES) return { text, truncated: false };
  return { text: lines.slice(0, PREVIEW_LINES).join("\n"), truncated: true };
}

type TimeRange = "today" | "7d" | "30d" | "all";

// ── Command Entry ───────────────────────────────────

function Entry({ log }: { log: CommandLogResponse }) {
  const [expanded, setExpanded] = useState(false);

  const failed = log.exit_code !== null && log.exit_code !== 0;
  const sec = log.security_level;
  const hasSec = sec && sec !== "allow";
  const hasOutput = !!(log.stdout || log.stderr);

  const stdout = log.stdout || "";
  const stderr = log.stderr || "";
  const stdoutT = truncate(stdout);
  const stderrT = truncate(stderr);
  const needsExpand = stdoutT.truncated || stderrT.truncated;

  return (
    <div
      className={clsx(
        "group border-b border-[#1a1a1a]",
        failed && "bg-[#1a0000]",
      )}
    >
      {/* Command line */}
      <div className="flex items-baseline px-4 py-2" style={mono}>
        {/* Time */}
        <span className="w-[72px] shrink-0 text-[12px] text-[#444]">
          {fmtTime(log.executed_at)}
        </span>

        {/* Prompt */}
        <span className="mr-1.5 text-[12px] text-[#555]">$</span>

        {/* Command */}
        <span
          className={clsx(
            "flex-1 text-[13px]",
            failed ? "text-[#ff6369]" : "text-[#e0e0e0]",
          )}
        >
          {log.command}
        </span>

        {/* Security badge */}
        {hasSec && (
          <span
            className={clsx(
              "mx-3 shrink-0 rounded-full px-2 py-[1px] text-[10px] font-medium",
              sec === "block" && "bg-[#ff0000]/10 text-[#ff4444]",
              sec === "confirm" && "bg-[#ff9500]/10 text-[#ff9500]",
              sec === "warn" && "bg-[#ffd60a]/8 text-[#ffd60a]",
            )}
          >
            {sec}
          </span>
        )}

        {/* Exit code */}
        <span
          className={clsx(
            "w-8 shrink-0 text-right text-[11px]",
            failed ? "text-[#ff4444]" : log.exit_code === 0 ? "text-[#30d158]" : "text-[#444]",
          )}
        >
          {log.exit_code !== null
            ? log.exit_code === 0
              ? "0"
              : String(log.exit_code)
            : "·"}
        </span>

        {/* Duration */}
        <span className="w-14 shrink-0 text-right text-[11px] text-[#333]">
          {fmtDuration(log.duration_ms)}
        </span>
      </div>

      {/* Output — default visible */}
      {hasOutput && (
        <div className="mx-4 mb-2 rounded border border-[#1a1a1a] bg-[#080808]">
          {stdout && (
            <pre
              className="overflow-x-auto px-3 py-2 text-[12px] leading-[1.6] text-[#888]"
              style={mono}
            >
              {expanded ? stdout : stdoutT.text}
            </pre>
          )}
          {stderr && (
            <pre
              className={clsx(
                "overflow-x-auto px-3 py-2 text-[12px] leading-[1.6] text-[#994444]",
                stdout && "border-t border-[#1a1a1a]",
              )}
              style={mono}
            >
              {expanded ? stderr : stderrT.text}
            </pre>
          )}
          {needsExpand && !expanded && (
            <button
              onClick={() => setExpanded(true)}
              className="flex w-full items-center gap-1 border-t border-[#1a1a1a] px-3 py-1.5 text-[11px] text-[#555] transition-colors hover:bg-[#111] hover:text-[#888]"
            >
              <ChevronRight size={10} />
              {stdout.split("\n").length + stderr.split("\n").length} lines total
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Activity Page ───────────────────────────────────

export default function Activity() {
  const { nodeId } = useParams<{ nodeId?: string }>();
  const [range, setRange] = useState<TimeRange>("today");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<CommandLogResponse[]>([]);
  const [live, setLive] = useState(false);
  const sentinel = useRef<HTMLDivElement>(null);

  const { data: node } = useNode(nodeId ?? "");

  useEffect(() => {
    setPage(1);
    setItems([]);
  }, [nodeId, range]);

  const { data, refetch, isFetching } = useLogs({
    node_id: nodeId,
    page,
    page_size: PAGE_SIZE,
  });

  // Accumulate pages
  useEffect(() => {
    if (!data?.items) return;
    if (page === 1) {
      setItems(data.items);
    } else {
      setItems((prev) => {
        const seen = new Set(prev.map((i) => i.id));
        return [...prev, ...data.items.filter((i) => !seen.has(i.id))];
      });
    }
  }, [data, page]);

  // Auto-refresh
  const tick = useCallback(() => void refetch(), [refetch]);
  useEffect(() => {
    if (!live) return;
    const id = setInterval(tick, 5000);
    return () => clearInterval(id);
  }, [live, tick]);

  // Infinite scroll
  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting && data && items.length < data.total && !isFetching) {
          setPage((p) => p + 1);
        }
      },
      { threshold: 0.1 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [data, items.length, isFetching]);

  const total = data?.total ?? 0;
  const csv = `/api/logs/export?format=csv${nodeId ? `&node_id=${nodeId}` : ""}`;

  const ranges: { label: string; value: TimeRange }[] = [
    { label: "Today", value: "today" },
    { label: "7d", value: "7d" },
    { label: "30d", value: "30d" },
    { label: "All", value: "all" },
  ];

  if (!nodeId) {
    return (
      <div className="flex h-full items-center justify-center bg-[#0a0a0a]">
        <p className="text-[13px] text-[#333]">Select a node</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-[#0e0e0e]">
      {/* Toolbar */}
      <div className="flex h-10 items-center justify-between border-b border-[#1a1a1a] bg-[#0a0a0a] px-4">
        <div className="flex items-center gap-4">
          {/* Node info */}
          <span className="text-[13px] font-medium text-[#ededed]">
            {node?.name ?? "…"}
          </span>
          <span className="text-[11px] text-[#444]">
            {node ? `${node.host}:${node.port}` : ""}
          </span>

          {/* Separator */}
          <span className="text-[#1a1a1a]">|</span>

          {/* Time pills */}
          <div className="flex gap-0.5">
            {ranges.map((r) => (
              <button
                key={r.value}
                onClick={() => setRange(r.value)}
                className={clsx(
                  "rounded px-2 py-0.5 text-[11px] font-medium transition-colors",
                  range === r.value
                    ? "bg-[#222] text-[#ededed]"
                    : "text-[#555] hover:text-[#999]",
                )}
              >
                {r.label}
              </button>
            ))}
          </div>

          <span className="text-[11px] tabular-nums text-[#333]">
            {total.toLocaleString()} cmd{total !== 1 ? "s" : ""}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <a
            href={csv}
            className="flex items-center gap-1 rounded px-2 py-1 text-[11px] text-[#555] transition-colors hover:bg-[#161616] hover:text-[#999]"
          >
            <Download size={11} strokeWidth={1.5} />
            CSV
          </a>
          <button
            onClick={() => setLive((v) => !v)}
            className={clsx(
              "flex items-center gap-1.5 rounded px-2 py-1 text-[11px] font-medium transition-colors",
              live
                ? "bg-[#30d158]/10 text-[#30d158]"
                : "text-[#555] hover:bg-[#161616] hover:text-[#999]",
            )}
          >
            <RefreshCw
              size={10}
              strokeWidth={1.5}
              className={live ? "animate-spin" : ""}
            />
            {live ? "Live" : "Auto"}
          </button>
        </div>
      </div>

      {/* Log body */}
      <div className="flex-1 overflow-y-auto">
        {items.length === 0 && !isFetching ? (
          <div className="flex h-full flex-col items-center justify-center gap-3">
            <Terminal size={20} strokeWidth={1} className="text-[#333]" />
            <p className="text-[13px] text-[#444]">No commands yet</p>
            <p className="text-[11px] text-[#333]">
              Commands will appear as AI executes them
            </p>
          </div>
        ) : (
          <>
            {items.map((log) => (
              <Entry key={log.id} log={log} />
            ))}
            <div ref={sentinel} className="h-px" />
            {isFetching && (
              <p className="py-4 text-center text-[11px] text-[#333]">
                Loading…
              </p>
            )}
            {!isFetching && items.length >= total && total > 0 && (
              <p className="py-4 text-center text-[11px] text-[#222]">
                — end —
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
