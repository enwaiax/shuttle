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
    { key: "pattern", label: "Pattern" },
    {
      key: "level",
      label: "Level",
      render: (r) => <Badge value={r.level} />,
    },
    {
      key: "description",
      label: "Description",
      render: (r) => r.description ?? "--",
    },
    { key: "priority", label: "Priority" },
    {
      key: "enabled",
      label: "Enabled",
      render: (r) => (r.enabled ? "Yes" : "No"),
    },
    {
      key: "_actions",
      label: "",
      render: (r) => (
        <button
          onClick={() => setDeleteTarget(r)}
          className="rounded-md p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
        >
          <Trash2 size={15} />
        </button>
      ),
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">
            Security Rules
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage command security rules.
          </p>
        </div>
        <button
          onClick={() => setFormOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
        >
          <Plus size={15} />
          Add Rule
        </button>
      </div>

      <div className="mt-6">
        {rules.length === 0 ? (
          <EmptyState
            icon={Shield}
            title="No rules yet"
            description="Add security rules to control command execution."
            action={
              <button
                onClick={() => setFormOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
              >
                <Plus size={14} />
                Add Rule
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
