import { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import { RefreshCw, Download, Terminal, ChevronRight } from "lucide-react";
import { useLogs, useNode } from "../api/client";
import type { CommandLogResponse } from "../api/client";
import clsx from "clsx";

const PAGE_SIZE = 50;
const PREVIEW_LINES = 15;

const mono = { fontFamily: "var(--font-mono)" };

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
        "group border-b border-[var(--border-subtle)] transition-colors",
        failed && "bg-[var(--red)]/[0.03]",
      )}
    >
      {/* Command line */}
      <div className="flex items-baseline px-5 py-2.5" style={mono}>
        <span className="w-[76px] shrink-0 text-[12px] text-[var(--text-quaternary)]">
          {fmtTime(log.executed_at)}
        </span>

        <span className="mr-2 text-[12px] text-[var(--green)]/60">$</span>

        <span
          className={clsx(
            "flex-1 text-[13px]",
            failed ? "text-[var(--red)]" : "text-[var(--text-primary)]",
          )}
        >
          {log.command}
        </span>

        {hasSec && (
          <span
            className={clsx(
              "mx-3 shrink-0 rounded-full px-2.5 py-[2px] text-[10px] font-semibold uppercase",
              sec === "block" && "bg-[var(--red-subtle)] text-[var(--red)]",
              sec === "confirm" && "bg-[var(--orange-subtle)] text-[var(--orange)]",
              sec === "warn" && "bg-[var(--yellow-subtle)] text-[var(--yellow)]",
            )}
          >
            {sec}
          </span>
        )}

        <span
          className={clsx(
            "w-8 shrink-0 text-right text-[11px] tabular-nums",
            failed
              ? "text-[var(--red)]"
              : log.exit_code === 0
                ? "text-[var(--green)]"
                : "text-[var(--text-quaternary)]",
          )}
        >
          {log.exit_code !== null
            ? log.exit_code === 0
              ? "0"
              : String(log.exit_code)
            : "·"}
        </span>

        <span className="w-14 shrink-0 text-right text-[11px] text-[var(--text-muted)]">
          {fmtDuration(log.duration_ms)}
        </span>
      </div>

      {/* Output */}
      {hasOutput && (
        <div className="mx-5 mb-3 overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-black">
          {stdout && (
            <pre
              className="overflow-x-auto px-4 py-2.5 text-[12px] leading-[1.7] text-[var(--text-tertiary)]"
              style={mono}
            >
              {expanded ? stdout : stdoutT.text}
            </pre>
          )}
          {stderr && (
            <pre
              className={clsx(
                "overflow-x-auto px-4 py-2.5 text-[12px] leading-[1.7] text-[var(--red)]/70",
                stdout && "border-t border-[var(--border-subtle)]",
              )}
              style={mono}
            >
              {expanded ? stderr : stderrT.text}
            </pre>
          )}
          {needsExpand && !expanded && (
            <button
              onClick={() => setExpanded(true)}
              className="flex w-full items-center gap-1.5 border-t border-[var(--border-subtle)] px-4 py-2 text-[11px] text-[var(--text-quaternary)] transition-colors hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-tertiary)]"
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

  const tick = useCallback(() => void refetch(), [refetch]);
  useEffect(() => {
    if (!live) return;
    const id = setInterval(tick, 5000);
    return () => clearInterval(id);
  }, [live, tick]);

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
      <div className="flex h-full items-center justify-center bg-black">
        <p className="text-[13px] text-[var(--text-muted)]">Select a node</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-black">
      {/* Toolbar */}
      <div className="flex h-12 items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-secondary)] px-5">
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-2.5">
            <span
              className={clsx(
                "h-2 w-2 rounded-full",
                node?.status === "active"
                  ? "bg-[var(--green)] animate-pulse-green"
                  : "bg-[var(--text-muted)]",
              )}
            />
            <span className="text-[14px] font-semibold text-[var(--text-primary)]">
              {node?.name ?? "…"}
            </span>
          </div>
          <span
            className="text-[12px] text-[var(--text-quaternary)]"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            {node ? `${node.host}:${node.port}` : ""}
          </span>

          <div className="h-4 w-px bg-[var(--border-subtle)]" />

          <div className="flex gap-0.5 rounded-lg bg-[var(--bg-tertiary)] p-0.5">
            {ranges.map((r) => (
              <button
                key={r.value}
                onClick={() => setRange(r.value)}
                className={clsx(
                  "rounded-md px-2.5 py-1 text-[11px] font-medium transition-all duration-200",
                  range === r.value
                    ? "bg-[var(--bg-elevated)] text-[var(--text-primary)] shadow-sm"
                    : "text-[var(--text-quaternary)] hover:text-[var(--text-tertiary)]",
                )}
              >
                {r.label}
              </button>
            ))}
          </div>

          <span className="text-[11px] tabular-nums text-[var(--text-muted)]" style={{ fontFamily: "var(--font-mono)" }}>
            {total.toLocaleString()} cmd{total !== 1 ? "s" : ""}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <a
            href={csv}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11px] font-medium text-[var(--text-quaternary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
          >
            <Download size={12} strokeWidth={1.5} />
            Export
          </a>
          <button
            onClick={() => setLive((v) => !v)}
            className={clsx(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11px] font-semibold transition-all duration-200",
              live
                ? "bg-[var(--green-subtle)] text-[var(--green)]"
                : "text-[var(--text-quaternary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]",
            )}
          >
            <RefreshCw
              size={11}
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
          <div className="flex h-full flex-col items-center justify-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--border-default)] bg-[var(--bg-elevated)]">
              <Terminal size={22} strokeWidth={1.2} className="text-[var(--text-quaternary)]" />
            </div>
            <div className="text-center">
              <p className="text-[14px] font-medium text-[var(--text-secondary)]">
                No commands yet
              </p>
              <p className="mt-1 text-[12px] text-[var(--text-quaternary)]">
                Commands will appear as AI executes them
              </p>
            </div>
          </div>
        ) : (
          <>
            {items.map((log) => (
              <Entry key={log.id} log={log} />
            ))}
            <div ref={sentinel} className="h-px" />
            {isFetching && (
              <p className="py-6 text-center text-[12px] text-[var(--text-muted)]">
                Loading…
              </p>
            )}
            {!isFetching && items.length >= total && total > 0 && (
              <p className="py-6 text-center text-[11px] text-[var(--text-muted)]">
                — end —
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
