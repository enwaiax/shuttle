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
    { key: "name", label: "Name", render: (r) => <span className="text-[#ededed]">{r.name}</span> },
    { key: "host", label: "Host", render: (r) => `${r.host}:${r.port}` },
    { key: "username", label: "User" },
    { key: "auth_type", label: "Auth" },
    { key: "status", label: "Status", render: (r) => <Badge value={r.status} /> },
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
          <h1 className="text-[15px] font-medium text-[#ededed]">Nodes</h1>
          <p className="mt-1 text-[13px] text-[#555]">Manage SSH connections</p>
        </div>
        <button
          onClick={() => setFormOpen(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-[#ededed] px-3 py-1.5 text-[13px] font-medium text-[#0a0a0a] hover:opacity-90"
        >
          <Plus size={14} />
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
                className="text-[13px] font-medium text-[#ededed] hover:text-white"
              >
                Add Node →
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
        onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}
        title="Delete Node"
        description={`Delete "${deleteTarget?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => { if (deleteTarget) deleteNode.mutate(deleteTarget.id); }}
      />
    </div>
  );
}
