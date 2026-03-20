import { useState } from "react";
import { ScrollText, ChevronLeft, ChevronRight } from "lucide-react";
import { useLogs } from "../api/client";
import type { CommandLogResponse } from "../api/client";
import type { Column } from "../components/DataTable";
import DataTable from "../components/DataTable";
import Badge from "../components/Badge";
import EmptyState from "../components/EmptyState";

const PAGE_SIZE = 20;

export default function Logs() {
  const [page, setPage] = useState(1);
  const { data } = useLogs({ page, page_size: PAGE_SIZE });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const columns: Column<CommandLogResponse>[] = [
    {
      key: "executed_at",
      label: "Time",
      render: (r) => new Date(r.executed_at).toLocaleString(),
    },
    {
      key: "node_name",
      label: "Node",
      render: (r) => r.node_name ?? "--",
    },
    {
      key: "command",
      label: "Command",
      render: (r) => (
        <code className="max-w-xs truncate text-xs">{r.command}</code>
      ),
    },
    {
      key: "exit_code",
      label: "Exit",
      render: (r) => (
        <span
          className={
            r.exit_code === 0
              ? "text-green-600"
              : r.exit_code != null
                ? "text-red-600"
                : "text-gray-400"
          }
        >
          {r.exit_code ?? "--"}
        </span>
      ),
    },
    {
      key: "security_level",
      label: "Level",
      render: (r) =>
        r.security_level ? <Badge value={r.security_level} /> : "--",
    },
    {
      key: "duration_ms",
      label: "Duration",
      render: (r) => (r.duration_ms != null ? `${r.duration_ms}ms` : "--"),
    },
  ];

  return (
    <div>
      <h1 className="text-lg font-semibold text-gray-900">Command Logs</h1>
      <p className="mt-1 text-sm text-gray-500">
        Audit trail of all executed commands.
      </p>

      <div className="mt-6">
        {items.length === 0 && page === 1 ? (
          <EmptyState
            icon={ScrollText}
            title="No logs yet"
            description="Command execution logs will appear here."
          />
        ) : (
          <>
            <DataTable columns={columns} data={items} keyField="id" />

            {/* Pagination */}
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Page {page} of {totalPages} ({total} total)
              </p>
              <div className="flex gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="inline-flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-40"
                >
                  <ChevronLeft size={14} />
                  Previous
                </button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="inline-flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:opacity-40"
                >
                  Next
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
