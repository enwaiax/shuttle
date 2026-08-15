import { useState } from "react";
import { Check, X, RefreshCw, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { useApprovals, useDecideApproval } from "../api/client";

export default function Approvals() {
  const [approver, setApprover] = useState("operator");
  const { data = [], isLoading, refetch } = useApprovals("pending");
  const decide = useDecideApproval();

  const submit = async (id: string, approve: boolean) => {
    try {
      await decide.mutateAsync({ id, approve, approver });
      toast.success(approve ? "Approved once" : "Denied");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Decision failed");
    }
  };

  return (
    <main className="flex-1 overflow-y-auto p-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-[var(--text-primary)]">
              Pending approvals
            </h1>
            <p className="mt-1 text-sm text-[var(--text-tertiary)]">
              Decisions are bound to one actor, conversation, node, and exact command.
            </p>
          </div>
          <button
            onClick={() => void refetch()}
            className="rounded-lg p-2 hover:bg-[var(--bg-hover)]"
            aria-label="Refresh"
          >
            <RefreshCw size={16} />
          </button>
        </div>

        <label className="mb-5 block text-xs text-[var(--text-tertiary)]">
          Approver identity
          <input
            value={approver}
            onChange={(event) => setApprover(event.target.value)}
            className="ml-3 rounded-md border border-[var(--border-default)] bg-[var(--bg-elevated)] px-3 py-1.5 text-[var(--text-primary)]"
          />
        </label>

        {isLoading && <p className="text-sm text-[var(--text-tertiary)]">Loading…</p>}
        {!isLoading && data.length === 0 && (
          <div className="rounded-xl border border-[var(--border-subtle)] p-12 text-center">
            <ShieldCheck className="mx-auto mb-3 text-[var(--green)]" />
            <p className="text-sm text-[var(--text-secondary)]">
              No commands are waiting for approval.
            </p>
          </div>
        )}
        <div className="space-y-4">
          {data.map((request) => (
            <article
              key={request.id}
              className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-elevated)] p-5"
            >
              <div className="mb-3 flex flex-wrap gap-2 text-xs text-[var(--text-tertiary)]">
                <span className="rounded bg-[var(--green-subtle)] px-2 py-1 text-[var(--green)]">
                  {request.node_name}
                </span>
                <span>{request.actor_id}</span><span>·</span>
                <span>{request.client_id}</span><span>·</span>
                <span>{request.conversation_id}</span>
              </div>
              <pre className="overflow-x-auto rounded-lg bg-[var(--bg-code)] p-4 text-sm text-[var(--text-primary)]">
                {request.command}
              </pre>
              {request.reason && (
                <p className="mt-3 text-xs text-[var(--text-tertiary)]">
                  Policy: {request.reason}
                </p>
              )}
              <div className="mt-4 flex justify-end gap-2">
                <button
                  disabled={!approver || decide.isPending}
                  onClick={() => void submit(request.id, false)}
                  className="flex items-center gap-1 rounded-lg border border-[var(--border-default)] px-3 py-2 text-sm hover:bg-[var(--red-subtle)]"
                >
                  <X size={14} /> Deny
                </button>
                <button
                  disabled={!approver || decide.isPending}
                  onClick={() => void submit(request.id, true)}
                  className="flex items-center gap-1 rounded-lg bg-[var(--green)] px-3 py-2 text-sm text-black"
                >
                  <Check size={14} /> Approve once
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}
