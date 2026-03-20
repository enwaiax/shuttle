import { useState } from "react";
import { Server, Plus, Trash2 } from "lucide-react";
import { useNodes, useDeleteNode } from "../api/client";
import type { NodeResponse } from "../types";
import type { Column } from "../components/DataTable";
import DataTable from "../components/DataTable";
import Badge from "../components/Badge";
import EmptyState from "../components/EmptyState";
import ConfirmDialog from "../components/ConfirmDialog";
import NodeForm from "./NodeForm";

export default function Nodes() {
  const { data: nodes = [] } = useNodes();
  const deleteNode = useDeleteNode();

  const [formOpen, setFormOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<NodeResponse | null>(null);

  const columns: Column<NodeResponse>[] = [
    { key: "name", label: "Name" },
    {
      key: "host",
      label: "Host",
      render: (r) => `${r.host}:${r.port}`,
    },
    { key: "username", label: "User" },
    { key: "auth_type", label: "Auth Type" },
    {
      key: "status",
      label: "Status",
      render: (r) => <Badge value={r.status} />,
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
          <h1 className="text-lg font-semibold text-gray-900">Nodes</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your SSH nodes.
          </p>
        </div>
        <button
          onClick={() => setFormOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
        >
          <Plus size={15} />
          Add Node
        </button>
      </div>

      <div className="mt-6">
        {nodes.length === 0 ? (
          <EmptyState
            icon={Server}
            title="No nodes yet"
            description="Add your first SSH node to get started."
            action={
              <button
                onClick={() => setFormOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
              >
                <Plus size={14} />
                Add Node
              </button>
            }
          />
        ) : (
          <DataTable columns={columns} data={nodes} keyField="id" />
        )}
      </div>

      <NodeForm open={formOpen} onOpenChange={setFormOpen} />

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="Delete Node"
        description={`Are you sure you want to delete "${deleteTarget?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => {
          if (deleteTarget) deleteNode.mutate(deleteTarget.id);
        }}
      />
    </div>
  );
}
