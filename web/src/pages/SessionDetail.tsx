import { useParams, Link } from "react-router-dom";
import { ChevronLeft, Terminal } from "lucide-react";
import { useSessions, useLogs } from "../api/client";
import Badge from "../components/Badge";

export default function SessionDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: sessions = [] } = useSessions();
  const session = sessions.find((s) => s.id === id);
  const { data: logData } = useLogs(id ? { session_id: id } : undefined);

  return (
    <div>
      <Link
        to="/sessions"
        className="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
      >
        <ChevronLeft size={14} />
        Back to Sessions
      </Link>

      {session ? (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-gray-100 p-2">
              <Terminal size={18} className="text-gray-500" strokeWidth={1.8} />
            </div>
            <div>
              <h1 className="text-base font-semibold text-gray-900">
                {session.node_name ?? session.node_id}
              </h1>
              <p className="text-sm text-gray-500">
                {session.working_directory ?? "No working directory"}
              </p>
            </div>
            <Badge value={session.status} className="ml-auto" />
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-gray-500">Created</dt>
              <dd className="mt-0.5 font-medium text-gray-900">
                {new Date(session.created_at).toLocaleString()}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500">Closed</dt>
              <dd className="mt-0.5 font-medium text-gray-900">
                {session.closed_at
                  ? new Date(session.closed_at).toLocaleString()
                  : "--"}
              </dd>
            </div>
          </dl>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-gray-500">Session not found.</p>
        </div>
      )}

      {/* Command history */}
      <h2 className="mt-8 text-sm font-semibold text-gray-900">
        Command History
      </h2>
      <div className="mt-3 space-y-2">
        {logData?.items.length === 0 && (
          <p className="text-sm text-gray-500">No commands recorded.</p>
        )}
        {logData?.items.map((log) => (
          <div
            key={log.id}
            className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm"
          >
            <div className="mt-0.5 h-2 w-2 flex-shrink-0 rounded-full bg-gray-300" />
            <div className="min-w-0 flex-1">
              <code className="block truncate text-sm text-gray-900">
                {log.command}
              </code>
              <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
                <span>
                  Exit:{" "}
                  <span
                    className={
                      log.exit_code === 0 ? "text-green-600" : "text-red-600"
                    }
                  >
                    {log.exit_code ?? "--"}
                  </span>
                </span>
                {log.duration_ms != null && (
                  <span>{log.duration_ms}ms</span>
                )}
                <span>{new Date(log.executed_at).toLocaleTimeString()}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
