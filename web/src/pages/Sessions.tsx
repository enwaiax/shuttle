import { Terminal, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useSessions, useCloseSession } from "../api/client";
import type { SessionResponse } from "../types";
import type { Column } from "../components/DataTable";
import DataTable from "../components/DataTable";
import Badge from "../components/Badge";
import EmptyState from "../components/EmptyState";

export default function Sessions() {
  const { data: sessions = [] } = useSessions();
  const closeSession = useCloseSession();
  const navigate = useNavigate();

  const columns: Column<SessionResponse>[] = [
    {
      key: "node_name",
      label: "Node",
      render: (r) => (
        <button
          onClick={() => navigate(`/sessions/${r.id}`)}
          className="font-medium text-blue-600 hover:underline"
        >
          {r.node_name ?? r.node_id}
        </button>
      ),
    },
    {
      key: "working_directory",
      label: "Working Directory",
      render: (r) => r.working_directory ?? "--",
    },
    {
      key: "status",
      label: "Status",
      render: (r) => <Badge value={r.status} />,
    },
    {
      key: "created_at",
      label: "Created",
      render: (r) => new Date(r.created_at).toLocaleString(),
    },
    {
      key: "_actions",
      label: "",
      render: (r) =>
        r.status === "active" ? (
          <button
            onClick={() => closeSession.mutate(r.id)}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-gray-500 hover:bg-red-50 hover:text-red-600"
          >
            <X size={13} />
            Close
          </button>
        ) : null,
    },
  ];

  return (
    <div>
      <h1 className="text-lg font-semibold text-gray-900">Sessions</h1>
      <p className="mt-1 text-sm text-gray-500">
        View and manage SSH sessions.
      </p>

      <div className="mt-6">
        {sessions.length === 0 ? (
          <EmptyState
            icon={Terminal}
            title="No sessions"
            description="Sessions will appear here when SSH connections are established."
          />
        ) : (
          <DataTable columns={columns} data={sessions} keyField="id" />
        )}
      </div>
    </div>
  );
}
