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
        <code className="text-[12px] text-[#ededed]" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
          {r.pattern}
        </code>
      ),
    },
    { key: "level", label: "Level", render: (r) => <Badge value={r.level} /> },
    { key: "description", label: "Description", render: (r) => r.description ?? "—" },
    { key: "priority", label: "Priority" },
    {
      key: "enabled",
      label: "Enabled",
      render: (r) => (
        <span className={r.enabled ? "text-[#30d158]" : "text-[#555]"}>
          {r.enabled ? "Yes" : "No"}
        </span>
      ),
    },
    {
      key: "_actions",
      label: "",
      render: (r) => (
        <button
          onClick={() => setDeleteTarget(r)}
          className="rounded-md p-1 text-[#444] hover:bg-[#ff4444]/10 hover:text-[#ff4444]"
        >
          <Trash2 size={14} />
        </button>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[15px] font-medium text-[#ededed]">Security Rules</h1>
          <p className="mt-1 text-[13px] text-[#555]">Control which commands require confirmation</p>
        </div>
        <button
          onClick={() => setFormOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-[#ededed] px-3 py-1.5 text-[13px] font-medium text-[#0a0a0a] hover:opacity-90"
        >
          <Plus size={14} />
          Add Rule
        </button>
      </div>

      <div className="mt-6">
        {rules.length === 0 ? (
          <EmptyState
            icon={Shield}
            title="No rules"
            description="Add security rules to control command execution."
            action={
              <button onClick={() => setFormOpen(true)} className="text-[13px] font-medium text-[#ededed] hover:text-white">
                Add Rule →
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
        onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}
        title="Delete Rule"
        description={`Delete rule "${deleteTarget?.pattern}"?`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => { if (deleteTarget) deleteRule.mutate(deleteTarget.id); }}
      />
    </div>
  );
}
