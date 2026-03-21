import { useState, useRef, useCallback, useMemo } from "react";
import { Shield, Plus, Trash2, Pencil, GripVertical, FlaskConical, X, ChevronDown, Globe, Server, ArrowDownRight } from "lucide-react";
import { useRules, useDeleteRule, useReorderRules, useUpdateRule, useNodes, useEffectiveRules } from "../api/client";
import type { RuleResponse } from "../types";
import Badge from "../components/Badge";
import EmptyState from "../components/EmptyState";
import ConfirmDialog from "../components/ConfirmDialog";
import { RuleSkeleton } from "../components/Skeleton";
import RuleForm from "./RuleForm";
import clsx from "clsx";

function EnableToggle({ rule }: { rule: RuleResponse }) {
  const update = useUpdateRule(rule.id);

  return (
    <button
      role="switch"
      aria-checked={rule.enabled}
      aria-label={`${rule.enabled ? "Disable" : "Enable"} rule ${rule.pattern}`}
      disabled={update.isPending}
      onClick={() => update.mutate({ enabled: !rule.enabled })}
      className={clsx(
        "relative inline-flex h-[20px] w-[36px] shrink-0 cursor-pointer items-center rounded-full border transition-all duration-200",
        rule.enabled
          ? "border-[var(--green)]/30 bg-[var(--green)]"
          : "border-[var(--border-default)] bg-[var(--bg-tertiary)]",
        update.isPending && "opacity-50",
      )}
    >
      <span
        className={clsx(
          "inline-block h-[14px] w-[14px] rounded-full bg-white shadow-sm transition-transform duration-200",
          rule.enabled ? "translate-x-[17px]" : "translate-x-[3px]",
        )}
      />
    </button>
  );
}

function RuleRow({
  rule,
  index,
  onEdit,
  onDelete,
  onDragStart,
  onDragOver,
  onDrop,
  isDragging,
}: {
  rule: RuleResponse;
  index: number;
  onEdit: (r: RuleResponse) => void;
  onDelete: (r: RuleResponse) => void;
  onDragStart: (i: number) => void;
  onDragOver: (e: React.DragEvent, i: number) => void;
  onDrop: () => void;
  isDragging: boolean;
}) {
  return (
    <div
      draggable
      onDragStart={() => onDragStart(index)}
      onDragOver={(e) => onDragOver(e, index)}
      onDrop={onDrop}
      onDragEnd={onDrop}
      className={clsx(
        "group flex items-center gap-4 border-b border-[var(--border-subtle)] px-5 py-3.5 transition-all duration-200",
        isDragging
          ? "opacity-50"
          : "hover:bg-[var(--bg-tertiary)]",
        !rule.enabled && !isDragging && "opacity-40",
      )}
    >
      <button
        aria-label="Drag to reorder"
        className="cursor-grab text-[var(--text-muted)] transition-colors active:cursor-grabbing group-hover:text-[var(--text-quaternary)]"
      >
        <GripVertical size={14} />
      </button>

      <code
        className="min-w-0 shrink-0 rounded-md bg-[var(--bg-elevated)] px-2.5 py-1 text-[12px] text-[var(--green)]"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {rule.pattern}
      </code>

      <Badge value={rule.level} />

      <span className="min-w-0 flex-1 truncate text-[13px] text-[var(--text-tertiary)]">
        {rule.description ?? "\u2014"}
      </span>

      <span
        className="shrink-0 text-[11px] tabular-nums text-[var(--text-quaternary)]"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        #{rule.priority}
      </span>

      <EnableToggle rule={rule} />

      <div className="flex shrink-0 items-center gap-1">
        <button
          onClick={() => onEdit(rule)}
          aria-label={`Edit rule ${rule.pattern}`}
          className="shrink-0 rounded-lg p-1.5 text-[var(--text-muted)] opacity-0 transition-all group-hover:opacity-100 hover:bg-[var(--blue-subtle)] hover:text-[var(--blue)]"
        >
          <Pencil size={14} />
        </button>
        <button
          onClick={() => onDelete(rule)}
          aria-label={`Delete rule ${rule.pattern}`}
          className="shrink-0 rounded-lg p-1.5 text-[var(--text-muted)] opacity-0 transition-all group-hover:opacity-100 hover:bg-[var(--red-subtle)] hover:text-[var(--red)]"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

type RuleSource = "inherited" | "overridden" | "node-only";

function SourceBadge({ source }: { source: RuleSource }) {
  const cls =
    source === "inherited"
      ? "bg-[var(--bg-tertiary)] text-[var(--text-quaternary)]"
      : source === "overridden"
        ? "bg-[var(--orange-subtle)] text-[var(--orange)]"
        : "bg-[var(--green-subtle)] text-[var(--green)]";
  return (
    <span className={clsx("shrink-0 rounded-full px-2 py-[2px] text-[10px] font-semibold uppercase", cls)}>
      {source}
    </span>
  );
}

function classifyRules(
  globalRules: RuleResponse[],
  effectiveRules: RuleResponse[],
): { rule: RuleResponse; source: RuleSource }[] {
  const globalIds = new Set(globalRules.map((r) => r.id));
  const globalPatterns = new Set(globalRules.map((r) => r.pattern));

  return effectiveRules.map((rule) => {
    if (globalIds.has(rule.id)) {
      return { rule, source: "inherited" as RuleSource };
    }
    if (rule.node_id && globalPatterns.has(rule.pattern)) {
      return { rule, source: "overridden" as RuleSource };
    }
    return { rule, source: "node-only" as RuleSource };
  });
}

export default function Rules() {
  const { data: rules = [], isLoading } = useRules();
  const { data: nodes = [] } = useNodes();
  const deleteRule = useDeleteRule();
  const reorder = useReorderRules();
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<RuleResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<RuleResponse | null>(null);
  const [testOpen, setTestOpen] = useState(false);
  const [testCmd, setTestCmd] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const dragIdx = useRef<number | null>(null);
  const [overIdx, setOverIdx] = useState<number | null>(null);

  const { data: effectiveRules, isLoading: effectiveLoading } = useEffectiveRules(selectedNodeId);

  const classifiedRules = useMemo(() => {
    if (!selectedNodeId || !effectiveRules) return null;
    return classifyRules(rules, effectiveRules);
  }, [rules, effectiveRules, selectedNodeId]);

  const handleDragStart = useCallback((i: number) => {
    dragIdx.current = i;
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, i: number) => {
    e.preventDefault();
    setOverIdx(i);
  }, []);

  const handleDrop = useCallback(() => {
    if (dragIdx.current === null || overIdx === null || dragIdx.current === overIdx) {
      dragIdx.current = null;
      setOverIdx(null);
      return;
    }
    const newOrder = [...rules];
    const [moved] = newOrder.splice(dragIdx.current, 1);
    newOrder.splice(overIdx, 0, moved);
    reorder.mutate(newOrder.map((r) => r.id));
    dragIdx.current = null;
    setOverIdx(null);
  }, [rules, overIdx, reorder]);

  const testMatch = testCmd
    ? rules.find((r) => {
        try {
          return new RegExp(r.pattern).test(testCmd);
        } catch {
          return false;
        }
      })
    : null;

  function openAddForm() {
    setEditTarget(null);
    setFormOpen(true);
  }

  function openEditForm(rule: RuleResponse) {
    setEditTarget(rule);
    setFormOpen(true);
  }

  function handleFormClose(open: boolean) {
    setFormOpen(open);
    if (!open) setEditTarget(null);
  }

  return (
    <div className="h-full overflow-y-auto bg-[var(--bg-primary)] p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[17px] font-bold tracking-[-0.02em] text-[var(--text-primary)]">
            Security Rules
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Control which commands require confirmation or are blocked.
            Drag to reorder priority.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setTestOpen((v) => !v)}
            className={clsx(
              "inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-[13px] font-medium transition-all duration-200",
              testOpen
                ? "border-[var(--green)]/30 bg-[var(--green-subtle)] text-[var(--green)]"
                : "border-[var(--border-default)] bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]",
            )}
          >
            <FlaskConical size={14} strokeWidth={1.8} />
            Test
          </button>
          <button
            onClick={openAddForm}
            className="inline-flex items-center gap-2 rounded-xl bg-[var(--green)] px-4 py-2.5 text-[13px] font-semibold text-black transition-all duration-200 hover:bg-[var(--green-light)] hover:shadow-[0_0_24px_rgba(118,185,0,0.3)]"
          >
            <Plus size={14} strokeWidth={2} />
            Add Rule
          </button>
        </div>
      </div>

      {/* Node effective rules preview */}
      <div className="mt-5 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-5">
        <div className="flex items-center gap-3">
          <Server size={14} className="text-[var(--text-quaternary)]" />
          <label htmlFor="node-select" className="shrink-0 text-[12px] font-medium text-[var(--text-secondary)]">
            Preview effective rules for node:
          </label>
          <div className="relative">
            <select
              id="node-select"
              value={selectedNodeId}
              onChange={(e) => setSelectedNodeId(e.target.value)}
              className="focus-ring h-9 appearance-none rounded-lg border border-[var(--border-default)] bg-[var(--bg-tertiary)] pl-4 pr-8 text-[13px] text-[var(--text-primary)] outline-none transition-all hover:border-[var(--border-strong)]"
            >
              <option value="">Global rules (default)</option>
              {nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name} ({n.host})
                </option>
              ))}
            </select>
            <ChevronDown size={12} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
          </div>
        </div>

        {selectedNodeId && (
          <div className="mt-4">
            {effectiveLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <RuleSkeleton key={i} />
                ))}
              </div>
            ) : classifiedRules && classifiedRules.length > 0 ? (
              <div className="overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-primary)]">
                <div className="flex items-center gap-4 border-b border-[var(--border-subtle)] px-5 py-2">
                  <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-quaternary)]">
                    Pattern
                  </span>
                  <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-quaternary)]">
                    Level
                  </span>
                  <span className="flex-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-quaternary)]">
                    Description
                  </span>
                  <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-quaternary)]">
                    Source
                  </span>
                </div>
                {classifiedRules.map(({ rule, source }) => (
                  <div
                    key={rule.id}
                    className="flex items-center gap-4 border-b border-[var(--border-subtle)] px-5 py-3 last:border-b-0"
                  >
                    <code
                      className="min-w-0 shrink-0 rounded-md bg-[var(--bg-elevated)] px-2.5 py-1 text-[12px] text-[var(--green)]"
                      style={{ fontFamily: "var(--font-mono)" }}
                    >
                      {rule.pattern}
                    </code>
                    <Badge value={rule.level} />
                    <span className="min-w-0 flex-1 truncate text-[13px] text-[var(--text-tertiary)]">
                      {rule.description ?? "—"}
                    </span>
                    <SourceBadge source={source} />
                  </div>
                ))}
              </div>
            ) : classifiedRules && classifiedRules.length === 0 ? (
              <p className="rounded-lg bg-[var(--bg-tertiary)] px-4 py-2.5 text-[12px] text-[var(--text-quaternary)]">
                No effective rules for this node.
              </p>
            ) : null}

            {classifiedRules && classifiedRules.length > 0 && (
              <div className="mt-3 flex items-center gap-4 text-[10px] text-[var(--text-muted)]">
                <span className="flex items-center gap-1">
                  <Globe size={10} /> inherited = global rule applied as-is
                </span>
                <span className="flex items-center gap-1">
                  <ArrowDownRight size={10} /> overridden = node rule replaces a global pattern
                </span>
                <span className="flex items-center gap-1">
                  <Server size={10} /> node-only = rule specific to this node
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Rule tester */}
      {testOpen && (
        <div className="animate-slide-up mt-5 rounded-2xl border border-[var(--border-default)] bg-[var(--bg-secondary)] p-5">
          <div className="flex items-center gap-3">
            <label htmlFor="test-cmd" className="shrink-0 text-[12px] font-medium text-[var(--text-secondary)]">
              Test command:
            </label>
            <div className="relative flex-1">
              <input
                id="test-cmd"
                type="text"
                value={testCmd}
                onChange={(e) => setTestCmd(e.target.value)}
                placeholder="Enter a command to test against rules…"
                className="focus-ring h-9 w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 text-[13px] text-[var(--text-primary)] outline-none transition-all placeholder:text-[var(--text-muted)] hover:border-[var(--border-strong)]"
                style={{ fontFamily: "var(--font-mono)" }}
              />
              {testCmd && (
                <button
                  onClick={() => setTestCmd("")}
                  aria-label="Clear test"
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                >
                  <X size={12} />
                </button>
              )}
            </div>
          </div>
          {testCmd && (
            <div className="mt-3">
              {testMatch ? (
                <div className="flex items-center gap-3 rounded-lg bg-[var(--bg-tertiary)] px-4 py-2.5">
                  <span className="text-[12px] text-[var(--text-secondary)]">Matches:</span>
                  <code
                    className="text-[12px] text-[var(--green)]"
                    style={{ fontFamily: "var(--font-mono)" }}
                  >
                    {testMatch.pattern}
                  </code>
                  <Badge value={testMatch.level} />
                  {testMatch.description && (
                    <span className="text-[12px] text-[var(--text-tertiary)]">
                      — {testMatch.description}
                    </span>
                  )}
                </div>
              ) : (
                <p className="rounded-lg bg-[var(--bg-tertiary)] px-4 py-2.5 text-[12px] text-[var(--success)]">
                  ✓ No rules match this command — it will be allowed
                </p>
              )}
            </div>
          )}
        </div>
      )}

      <div className="mt-7">
        {isLoading ? (
          <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
            {Array.from({ length: 4 }).map((_, i) => (
              <RuleSkeleton key={i} />
            ))}
          </div>
        ) : rules.length === 0 ? (
          <EmptyState
            icon={Shield}
            title="No rules configured"
            description="Add security rules to control command execution. Rules can block, require confirmation, or warn on specific command patterns."
            action={
              <button
                onClick={openAddForm}
                className="text-[13px] font-semibold text-[var(--green)] transition-colors hover:text-[var(--green-light)]"
              >
                Add your first rule →
              </button>
            }
          />
        ) : (
          <div className="overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
            <div className="flex items-center gap-4 border-b border-[var(--border-subtle)] px-5 py-2.5">
              <span className="w-[14px]" />
              <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-quaternary)]">
                Pattern
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-quaternary)]">
                Level
              </span>
              <span className="flex-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-quaternary)]">
                Description
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-quaternary)]">
                Priority
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-quaternary)]">
                Enabled
              </span>
              <span className="w-[62px]" />
            </div>
            {rules.map((rule, i) => (
              <RuleRow
                key={rule.id}
                rule={rule}
                index={i}
                onEdit={openEditForm}
                onDelete={setDeleteTarget}
                onDragStart={handleDragStart}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                isDragging={dragIdx.current === i}
              />
            ))}
          </div>
        )}
      </div>

      <RuleForm open={formOpen} onOpenChange={handleFormClose} rule={editTarget} />

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="Delete Rule"
        description={`Are you sure you want to delete the rule "${deleteTarget?.pattern}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => {
          if (deleteTarget) deleteRule.mutate(deleteTarget.id);
        }}
      />
    </div>
  );
}
