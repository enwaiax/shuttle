import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  RefreshCw,
  Download,
  Terminal,
  ChevronRight,
  ChevronLeft,
  Search,
  Copy,
  Check,
  X,
  FileText,
  ClipboardCopy,
} from "lucide-react";
import { useLogs, useNode } from "../api/client";
import type { CommandLogResponse } from "../api/client";
import { CommandSkeleton } from "../components/Skeleton";
import { useApp } from "../hooks/AppContext";
import clsx from "clsx";

const PAGE_SIZE = 50;
const PREVIEW_LINES = 15;
const MAX_EXPANDED_LINES = 200;
const MAX_ITEMS_IN_DOM = 200;

const mono = { fontFamily: "var(--font-mono)" };

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function fmtDuration(ms: number | null): string {
  if (ms == null) return "";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60_000)}m${Math.floor((ms % 60_000) / 1000)}s`;
}

function truncate(text: string) {
  const lines = text.split("\n");
  if (lines.length <= PREVIEW_LINES) return { text, truncated: false, totalLines: lines.length };
  return { text: lines.slice(0, PREVIEW_LINES).join("\n"), truncated: true, totalLines: lines.length };
}

function expandedText(text: string): { text: string; capped: boolean; totalLines: number } {
  const lines = text.split("\n");
  if (lines.length <= MAX_EXPANDED_LINES) return { text, capped: false, totalLines: lines.length };
  return {
    text: lines.slice(0, MAX_EXPANDED_LINES).join("\n"),
    capped: true,
    totalLines: lines.length,
  };
}

function formatLogAsText(log: CommandLogResponse): string {
  const time = fmtTime(log.executed_at);
  const exit = log.exit_code !== null ? `exit:${log.exit_code}` : "";
  const dur = fmtDuration(log.duration_ms);
  const sec = log.security_level && log.security_level !== "allow" ? `[${log.security_level.toUpperCase()}]` : "";
  const meta = [sec, exit, dur].filter(Boolean).join("  ");
  let line = `[${time}] $ ${log.command}`;
  if (meta) line += `  ${meta}`;

  if (log.stdout) {
    line += "\n" + log.stdout.split("\n").map((l) => `    ${l}`).join("\n");
  }
  if (log.stderr) {
    line += "\n" + log.stderr.split("\n").map((l) => `  ! ${l}`).join("\n");
  }
  return line;
}

type TimeRange = "today" | "7d" | "30d" | "all";
type LevelFilter = "all" | "block" | "confirm" | "warn";

function computeSince(range: TimeRange): string | undefined {
  if (range === "all") return undefined;
  const now = new Date();
  if (range === "today") {
    now.setHours(0, 0, 0, 0);
  } else if (range === "7d") {
    now.setDate(now.getDate() - 7);
    now.setHours(0, 0, 0, 0);
  } else if (range === "30d") {
    now.setDate(now.getDate() - 30);
    now.setHours(0, 0, 0, 0);
  }
  return now.toISOString();
}

function InlineCopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      onClick={handleCopy}
      aria-label="Copy command"
      className="shrink-0 rounded-md p-1 text-[var(--text-muted)] opacity-0 transition-all group-hover:opacity-100 hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
    >
      {copied ? <Check size={12} className="text-[var(--green)]" /> : <Copy size={12} />}
    </button>
  );
}

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
  const stdoutE = expandedText(stdout);
  const stderrE = expandedText(stderr);

  return (
    <div
      className={clsx(
        "group border-b border-[var(--border-subtle)] transition-colors",
        failed && "bg-[var(--red)]/[0.03]",
      )}
    >
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
        <InlineCopyButton text={log.command} />
        {hasSec && (
          <span
            className={clsx(
              "mx-2 shrink-0 rounded-full px-2.5 py-[2px] text-[10px] font-semibold uppercase",
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
            failed ? "text-[var(--red)]" : log.exit_code === 0 ? "text-[var(--green)]" : "text-[var(--text-quaternary)]",
          )}
        >
          {log.exit_code !== null ? (log.exit_code === 0 ? "0" : String(log.exit_code)) : "·"}
        </span>
        <span className="w-14 shrink-0 text-right text-[11px] text-[var(--text-muted)]">
          {fmtDuration(log.duration_ms)}
        </span>
      </div>

      {hasOutput && (
        <div className="mx-5 mb-3 overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-code)] shadow-[var(--shadow-card)]">
          <div className="border-l-2 border-[var(--green)]/30">
            {stdout && (
              <pre className="overflow-x-auto px-4 py-2.5 text-[12px] leading-[1.7] text-[var(--text-tertiary)]" style={mono}>
                {expanded ? stdoutE.text : stdoutT.text}
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
                {expanded ? stderrE.text : stderrT.text}
              </pre>
            )}
          </div>
          {needsExpand && !expanded && (
            <button
              onClick={() => setExpanded(true)}
              className="flex w-full items-center gap-1.5 border-t border-[var(--border-subtle)] px-4 py-2 text-[11px] text-[var(--text-quaternary)] transition-colors hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-tertiary)]"
            >
              <ChevronRight size={10} />
              {stdoutT.totalLines + stderrT.totalLines} lines total
            </button>
          )}
          {expanded && (stdoutE.capped || stderrE.capped) && (
            <div className="border-t border-[var(--border-subtle)] px-4 py-2 text-[11px] text-[var(--text-muted)]">
              Showing first {MAX_EXPANDED_LINES} of {stdoutE.totalLines + stderrE.totalLines} lines
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DateSeparator({ label }: { label: string }) {
  return (
    <div className="glass-toolbar sticky top-0 z-10 flex items-center gap-3 border-b border-[var(--border-subtle)] px-5 py-2.5">
      <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--text-tertiary)]">
        {label}
      </span>
      <div className="h-px flex-1 bg-[var(--border-default)]" />
    </div>
  );
}

function CopyAllButton({ items }: { items: CommandLogResponse[] }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    const text = items.map(formatLogAsText).join("\n\n");
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      aria-label="Copy all visible commands"
      className={clsx(
        "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11px] font-medium transition-all duration-200",
        copied
          ? "bg-[var(--green-subtle)] text-[var(--green)]"
          : "text-[var(--text-quaternary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]",
      )}
    >
      {copied ? <Check size={12} /> : <ClipboardCopy size={12} strokeWidth={1.5} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function RawView({ items }: { items: CommandLogResponse[] }) {
  const text = useMemo(() => items.map(formatLogAsText).join("\n\n"), [items]);

  return (
    <div className="bg-[var(--bg-primary)]">
      <pre
        className="whitespace-pre-wrap p-5 text-[12px] leading-[1.8] text-[var(--text-secondary)]"
        style={mono}
      >
        {text || "No commands to display"}
      </pre>
    </div>
  );
}

export default function Activity() {
  const { nodeId } = useParams<{ nodeId?: string }>();
  const navigate = useNavigate();
  const [range, setRange] = useState<TimeRange>("today");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<CommandLogResponse[]>([]);
  const [live, setLive] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [levelFilter, setLevelFilter] = useState<LevelFilter>("all");
  const [rawMode, setRawMode] = useState(false);
  const sentinel = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const logBodyRef = useRef<HTMLDivElement>(null);

  const { data: node } = useNode(nodeId ?? "");
  const { trackNode } = useApp();

  useEffect(() => {
    if (node) {
      trackNode({ id: node.id, name: node.name, status: node.status });
    }
  }, [node, trackNode]);

  useEffect(() => {
    setPage(1);
    setItems([]);
  }, [nodeId, range]);

  const since = useMemo(() => computeSince(range), [range]);

  const { data, refetch, isFetching } = useLogs({
    node_id: nodeId,
    page,
    page_size: PAGE_SIZE,
    since,
  });

  useEffect(() => {
    if (!data?.items) return;
    if (page === 1) {
      setItems(data.items);
    } else {
      setItems((prev) => {
        const seen = new Set(prev.map((i) => i.id));
        const merged = [...prev, ...data.items.filter((i) => !seen.has(i.id))];
        // Cap DOM items to prevent memory bloat on long scroll sessions
        return merged.slice(-MAX_ITEMS_IN_DOM);
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

  useEffect(() => {
    if (searchOpen) searchRef.current?.focus();
  }, [searchOpen]);

  useEffect(() => {
    function handleSelectAll(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "a") {
        const active = document.activeElement;
        if (active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement) return;

        const el = logBodyRef.current;
        if (!el) return;

        e.preventDefault();
        const selection = window.getSelection();
        if (!selection) return;
        const range = document.createRange();
        range.selectNodeContents(el);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    }
    document.addEventListener("keydown", handleSelectAll);
    return () => document.removeEventListener("keydown", handleSelectAll);
  }, []);

  const filteredItems = useMemo(() => {
    let result = items;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter((i) => i.command.toLowerCase().includes(q));
    }
    if (levelFilter !== "all") {
      result = result.filter((i) => i.security_level === levelFilter);
    }
    return result;
  }, [items, searchQuery, levelFilter]);

  const groupedItems = useMemo(() => {
    const groups: { date: string; items: CommandLogResponse[] }[] = [];
    let currentDate = "";
    for (const item of filteredItems) {
      const d = fmtDate(item.executed_at);
      if (d !== currentDate) {
        currentDate = d;
        groups.push({ date: d, items: [] });
      }
      groups[groups.length - 1].items.push(item);
    }
    return groups;
  }, [filteredItems]);

  const total = data?.total ?? 0;
  const csv = `/api/logs/export?format=csv${nodeId ? `&node_id=${nodeId}` : ""}`;

  const ranges: { label: string; value: TimeRange }[] = [
    { label: "Today", value: "today" },
    { label: "7d", value: "7d" },
    { label: "30d", value: "30d" },
    { label: "All", value: "all" },
  ];

  const levels: { label: string; value: LevelFilter }[] = [
    { label: "All", value: "all" },
    { label: "Block", value: "block" },
    { label: "Confirm", value: "confirm" },
    { label: "Warn", value: "warn" },
  ];

  if (!nodeId) {
    return (
      <div className="flex h-full items-center justify-center bg-[var(--bg-primary)]">
        <p className="text-[13px] text-[var(--text-muted)]">Select a node</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-[var(--bg-primary)]">
      {/* Breadcrumb */}
      <div className="glass-toolbar select-none-chrome flex h-10 items-center gap-2 border-b border-[var(--border-subtle)] px-5">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[12px] text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
        >
          <ChevronLeft size={12} strokeWidth={1.5} />
          Nodes
        </button>
        <span className="text-[12px] text-[var(--text-muted)]">/</span>
        <span className="text-[12px] font-medium text-[var(--text-primary)]">
          {node?.name ?? "…"}
        </span>
      </div>

      {/* Brand accent line */}
      <div className="h-[1px]" style={{ background: "var(--brand-line)" }} />

      {/* Toolbar */}
      <div className="glass-toolbar select-none-chrome flex h-11 items-center justify-between border-b border-[var(--border-subtle)] px-5">
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-2.5">
            <span
              className={clsx(
                "h-2 w-2 rounded-full",
                node?.status === "active" ? "bg-[var(--green)] animate-pulse-green" : "bg-[var(--text-muted)]",
              )}
            />
            <span className="text-[12px] text-[var(--text-quaternary)]" style={mono}>
              {node ? `${node.host}:${node.port}` : ""}
            </span>
          </div>

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

          <span className="text-[11px] tabular-nums text-[var(--text-muted)]" style={mono}>
            {total.toLocaleString()} cmd{total !== 1 ? "s" : ""}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <CopyAllButton items={filteredItems} />
          <a
            href={csv}
            aria-label="Export as CSV"
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11px] font-medium text-[var(--text-quaternary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
          >
            <Download size={12} strokeWidth={1.5} />
            CSV
          </a>
          <button
            onClick={() => setSearchOpen((v) => !v)}
            aria-label="Toggle search"
            className={clsx(
              "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-medium transition-all duration-200",
              searchOpen
                ? "bg-[var(--green-subtle)] text-[var(--green)]"
                : "text-[var(--text-quaternary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]",
            )}
          >
            <Search size={11} strokeWidth={1.5} />
          </button>
          <button
            onClick={() => setRawMode((v) => !v)}
            aria-label={rawMode ? "Switch to styled view" : "Switch to raw text view"}
            className={clsx(
              "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-medium transition-all duration-200",
              rawMode
                ? "bg-[var(--green-subtle)] text-[var(--green)]"
                : "text-[var(--text-quaternary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]",
            )}
          >
            <FileText size={11} strokeWidth={1.5} />
            Raw
          </button>
          <button
            onClick={() => setLive((v) => !v)}
            aria-label={live ? "Disable auto-refresh" : "Enable auto-refresh"}
            className={clsx(
              "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition-all duration-200",
              live
                ? "bg-[var(--green-subtle)] text-[var(--green)]"
                : "text-[var(--text-quaternary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]",
            )}
          >
            <RefreshCw size={11} strokeWidth={1.5} className={live ? "animate-spin" : ""} />
            {live ? "Live" : "Auto"}
          </button>
        </div>
      </div>

      {/* Search & Filter bar */}
      {(searchOpen || levelFilter !== "all") && (
        <div className="glass-toolbar select-none-chrome animate-slide-down flex items-center gap-3 border-b border-[var(--border-subtle)] px-5 py-2">
          {searchOpen && (
            <div className="relative flex-1">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
              <input
                ref={searchRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search commands…"
                aria-label="Search commands"
                className="focus-ring h-8 w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-tertiary)] pl-9 pr-8 text-[12px] text-[var(--text-primary)] outline-none transition-all placeholder:text-[var(--text-muted)] hover:border-[var(--border-strong)]"
                style={mono}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  aria-label="Clear search"
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                >
                  <X size={12} />
                </button>
              )}
            </div>
          )}

          <div className="flex gap-0.5 rounded-lg bg-[var(--bg-tertiary)] p-0.5">
            {levels.map((l) => (
              <button
                key={l.value}
                onClick={() => setLevelFilter(l.value)}
                className={clsx(
                  "rounded-md px-2.5 py-1 text-[10px] font-semibold uppercase transition-all duration-200",
                  levelFilter === l.value
                    ? l.value === "block"
                      ? "bg-[var(--red-subtle)] text-[var(--red)]"
                      : l.value === "confirm"
                        ? "bg-[var(--orange-subtle)] text-[var(--orange)]"
                        : l.value === "warn"
                          ? "bg-[var(--yellow-subtle)] text-[var(--yellow)]"
                          : "bg-[var(--bg-elevated)] text-[var(--text-primary)] shadow-sm"
                    : "text-[var(--text-quaternary)] hover:text-[var(--text-tertiary)]",
                )}
              >
                {l.label}
              </button>
            ))}
          </div>

          {(searchQuery || levelFilter !== "all") && (
            <span className="text-[10px] tabular-nums text-[var(--text-muted)]">
              {filteredItems.length} result{filteredItems.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      )}

      {/* Log body — Raw or Styled */}
      {rawMode ? (
        <div ref={logBodyRef} className="flex-1 overflow-y-auto">
          <RawView items={filteredItems} />
        </div>
      ) : (
        <div ref={logBodyRef} className="flex-1 overflow-y-auto">
          {items.length === 0 && isFetching ? (
            <div>
              {Array.from({ length: 8 }).map((_, i) => (
                <CommandSkeleton key={i} />
              ))}
            </div>
          ) : filteredItems.length === 0 && !isFetching ? (
            <div className="flex h-full flex-col items-center justify-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--border-default)] bg-[var(--bg-elevated)]">
                <Terminal size={22} strokeWidth={1.2} className="text-[var(--text-quaternary)]" />
              </div>
              <div className="text-center">
                <p className="text-[14px] font-medium text-[var(--text-secondary)]">
                  {searchQuery || levelFilter !== "all" ? "No matching commands" : "No commands yet"}
                </p>
                <p className="mt-1 text-[12px] text-[var(--text-quaternary)]">
                  {searchQuery || levelFilter !== "all"
                    ? "Try adjusting your search or filters"
                    : "Commands will appear as AI executes them"}
                </p>
              </div>
            </div>
          ) : (
            <>
              {groupedItems.map((group) => (
                <div key={group.date}>
                  <DateSeparator label={group.date} />
                  {group.items.map((log) => (
                    <Entry key={log.id} log={log} />
                  ))}
                </div>
              ))}
              <div ref={sentinel} className="h-px" />
              {isFetching && (
                <p className="py-6 text-center text-[12px] text-[var(--text-muted)]">Loading…</p>
              )}
              {!isFetching && items.length >= total && total > 0 && (
                <p className="py-6 text-center text-[11px] text-[var(--text-muted)]">— end —</p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
