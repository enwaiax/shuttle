import { useState } from "react";
import { Shield, Plus, Trash2 } from "lucide-react";
import { useRules, useDeleteRule } from "../api/client";
import type { RuleResponse } from "../types";
import type { Column } from "../components/DataTable";
import DataTable from "../components/DataTable";
import Badge from "../components/Badge";
import EmptyState from "../components/EmptyState";
import ConfirmDialog from "../components/ConfirmDialog";
import RuleForm from "./RuleForm";

export default function Rules() {
  const { data: rules = [] } = useRules();
  const deleteRule = useDeleteRule();
  const [formOpen, setFormOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<RuleResponse | null>(null);

  const columns: Column<RuleResponse>[] = [
    {
      key: "pattern",
      label: "Pattern",
      render: (r) => (
        <code
          className="rounded-md bg-[var(--bg-elevated)] px-2 py-0.5 text-[12px] text-[var(--green)]"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {r.pattern}
        </code>
      ),
    },
    {
      key: "level",
      label: "Level",
      render: (r) => <Badge value={r.level} />,
    },
    {
      key: "description",
      label: "Description",
      render: (r) => (
        <span className="text-[var(--text-tertiary)]">{r.description ?? "—"}</span>
      ),
    },
    {
      key: "priority",
      label: "Priority",
      render: (r) => (
        <span className="tabular-nums" style={{ fontFamily: "var(--font-mono)" }}>
          {r.priority}
        </span>
      ),
    },
    {
      key: "enabled",
      label: "Status",
      render: (r) => (
        <span
          className={
            r.enabled ? "text-[var(--green)]" : "text-[var(--text-quaternary)]"
          }
        >
          {r.enabled ? "Active" : "Disabled"}
        </span>
      ),
    },
    {
      key: "_actions",
      label: "",
      render: (r) => (
        <button
          onClick={() => setDeleteTarget(r)}
          className="rounded-lg p-1.5 text-[var(--text-quaternary)] transition-colors hover:bg-[var(--red-subtle)] hover:text-[var(--red)]"
        >
          <Trash2 size={14} />
        </button>
      ),
    },
  ];

  return (
    <div className="h-full overflow-y-auto bg-black p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[17px] font-bold tracking-[-0.02em] text-[var(--text-primary)]">
            Security Rules
          </h1>
          <p className="mt-1 text-[13px] text-[var(--text-tertiary)]">
            Control which commands require confirmation or are blocked
          </p>
        </div>
        <button
          onClick={() => setFormOpen(true)}
          className="inline-flex items-center gap-2 rounded-xl bg-[var(--green)] px-4 py-2.5 text-[13px] font-semibold text-black transition-all duration-200 hover:bg-[var(--green-light)] hover:shadow-[0_0_24px_rgba(118,185,0,0.3)]"
        >
          <Plus size={14} strokeWidth={2} />
          Add Rule
        </button>
      </div>

      <div className="mt-7">
        {rules.length === 0 ? (
          <EmptyState
            icon={Shield}
            title="No rules configured"
            description="Add security rules to control command execution. Rules can block, require confirmation, or warn on specific command patterns."
            action={
              <button
                onClick={() => setFormOpen(true)}
                className="text-[13px] font-semibold text-[var(--green)] transition-colors hover:text-[var(--green-light)]"
              >
                Add your first rule →
              </button>
            }
          />
        ) : (
          <DataTable columns={columns} data={rules} keyField="id" />
        )}
      </div>

      <RuleForm open={formOpen} onOpenChange={setFormOpen} />

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
