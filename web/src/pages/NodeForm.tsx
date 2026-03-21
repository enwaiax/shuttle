import { useState, useEffect } from "react";
import { X, Server, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { useCreateNode, useUpdateNode, useNode, useNodes } from "../api/client";

interface NodeFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  nodeId?: string | null;
}

const inputCls =
  "focus-ring w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-3 py-2.5 text-[13px] text-[var(--text-primary)] outline-none transition-all duration-200 placeholder:text-[var(--text-muted)] hover:border-[var(--border-strong)]";

const labelCls = "mb-1.5 block text-[12px] font-medium text-[var(--text-secondary)]";

const sectionCls = "border-b border-[var(--border-subtle)] pb-5 mb-5";

export default function NodeForm({ open, onOpenChange, nodeId }: NodeFormProps) {
  const isEdit = !!nodeId;
  const { data: existingNode } = useNode(nodeId ?? "");
  const { data: allNodes } = useNodes();

  const [name, setName] = useState("");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("22");
  const [username, setUsername] = useState("");
  const [authType, setAuthType] = useState<"password" | "key">("password");
  const [password, setPassword] = useState("");
  const [jumpHostId, setJumpHostId] = useState<string>("");
  const [tags, setTags] = useState("");

  const create = useCreateNode();
  const update = useUpdateNode(nodeId ?? "");

  useEffect(() => {
    if (isEdit && existingNode) {
      setName(existingNode.name);
      setHost(existingNode.host);
      setPort(String(existingNode.port));
      setUsername(existingNode.username);
      setAuthType(existingNode.auth_type === "key" ? "key" : "password");
      setPassword("");
      setJumpHostId(existingNode.jump_host_id ?? "");
      setTags(existingNode.tags?.join(", ") ?? "");
    } else if (!isEdit) {
      // Reset all fields when opening in create mode
      setName(""); setHost(""); setPort("22"); setUsername("");
      setAuthType("password"); setPassword(""); setJumpHostId(""); setTags("");
    }
  }, [isEdit, existingNode]);

  // Available jump hosts: all nodes except current one
  const jumpHostOptions = (allNodes ?? []).filter((n) => n.id !== nodeId);

  function reset() {
    setName("");
    setHost("");
    setPort("22");
    setUsername("");
    setAuthType("password");
    setPassword("");
    setJumpHostId("");
    setTags("");
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const parsedTags = tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);

    if (isEdit) {
      update.mutate(
        {
          name,
          host,
          port: Number(port),
          username,
          jump_host_id: jumpHostId || null,
          tags: parsedTags.length > 0 ? parsedTags : null,
          ...(password ? { credential: password, auth_type: authType } : {}),
        },
        { onSuccess: () => { toast.success(`Node "${name}" updated`); reset(); onOpenChange(false); }, onError: (err) => toast.error(err.message) },
      );
    } else {
      create.mutate(
        {
          name,
          host,
          port: Number(port),
          username,
          auth_type: authType,
          credential: password,
          jump_host_id: jumpHostId || null,
          tags: parsedTags.length > 0 ? parsedTags : null,
        },
        { onSuccess: () => { toast.success(`Node "${name}" created`); reset(); onOpenChange(false); }, onError: (err) => toast.error(err.message) },
      );
    }
  }

  const isPending = isEdit ? update.isPending : create.isPending;

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={() => onOpenChange(false)}
      />

      {/* Slide-over panel */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg animate-slide-in-right">
        <div className="flex h-full w-full flex-col border-l border-[var(--border-default)] bg-[var(--bg-elevated)] shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--green-subtle)]">
                <Server size={16} className="text-[var(--green)]" />
              </div>
              <h2 className="text-[15px] font-semibold text-[var(--text-primary)]">
                {isEdit ? "Edit Node" : "Add Node"}
              </h2>
            </div>
            <button
              onClick={() => onOpenChange(false)}
              className="rounded-lg p-2 text-[var(--text-quaternary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
            >
              <X size={16} />
            </button>
          </div>

          {/* Form body — scrollable */}
          <form onSubmit={handleSubmit} className="flex flex-1 flex-col overflow-y-auto px-6 py-5">
            {/* Connection section */}
            <div className={sectionCls}>
              <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-quaternary)]">
                Connection
              </h3>
              <div className="space-y-3">
                <div>
                  <label className={labelCls}>Node Name</label>
                  <input
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="my-gpu-server"
                    className={inputCls}
                  />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <label className={labelCls}>Host</label>
                    <input
                      required
                      value={host}
                      onChange={(e) => setHost(e.target.value)}
                      placeholder="192.168.1.100 or hostname.com"
                      className={inputCls}
                      style={{ fontFamily: "var(--font-mono)" }}
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Port</label>
                    <input
                      required
                      type="number"
                      value={port}
                      onChange={(e) => setPort(e.target.value)}
                      className={inputCls}
                      style={{ fontFamily: "var(--font-mono)" }}
                    />
                  </div>
                </div>
                <div>
                  <label className={labelCls}>Username</label>
                  <input
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="root"
                    className={inputCls}
                    style={{ fontFamily: "var(--font-mono)" }}
                  />
                </div>
              </div>
            </div>

            {/* Authentication section */}
            <div className={sectionCls}>
              <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-quaternary)]">
                Authentication
              </h3>
              <div className="space-y-3">
                <div>
                  <label className={labelCls}>Auth Type</label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setAuthType("password")}
                      className={`flex-1 rounded-lg border px-3 py-2 text-[13px] font-medium transition-all ${
                        authType === "password"
                          ? "border-[var(--green)] bg-[var(--green-subtle)] text-[var(--green)]"
                          : "border-[var(--border-default)] bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:border-[var(--border-strong)]"
                      }`}
                    >
                      Password
                    </button>
                    <button
                      type="button"
                      onClick={() => setAuthType("key")}
                      className={`flex-1 rounded-lg border px-3 py-2 text-[13px] font-medium transition-all ${
                        authType === "key"
                          ? "border-[var(--green)] bg-[var(--green-subtle)] text-[var(--green)]"
                          : "border-[var(--border-default)] bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:border-[var(--border-strong)]"
                      }`}
                    >
                      SSH Key
                    </button>
                  </div>
                </div>
                <div>
                  <label className={labelCls}>
                    {authType === "password" ? "Password" : "Private Key Content"}
                    {isEdit ? " (leave blank to keep current)" : ""}
                  </label>
                  {authType === "password" ? (
                    <input
                      required={!isEdit}
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className={inputCls}
                    />
                  ) : (
                    <textarea
                      required={!isEdit}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="-----BEGIN OPENSSH PRIVATE KEY-----&#10;..."
                      rows={4}
                      className={inputCls + " resize-none"}
                      style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}
                    />
                  )}
                </div>
              </div>
            </div>

            {/* Jump Host section */}
            <div className={sectionCls}>
              <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-quaternary)]">
                Jump Host (Bastion)
              </h3>
              <div>
                <label className={labelCls}>Connect via</label>
                <div className="relative">
                  <select
                    value={jumpHostId}
                    onChange={(e) => setJumpHostId(e.target.value)}
                    className={inputCls + " appearance-none pr-10"}
                  >
                    <option value="">Direct connection (no jump host)</option>
                    {jumpHostOptions.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.name} ({n.host}:{n.port})
                      </option>
                    ))}
                  </select>
                  <ChevronDown
                    size={14}
                    className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-quaternary)]"
                  />
                </div>
                {jumpHostId && (
                  <p className="mt-2 text-[11px] text-[var(--text-tertiary)]">
                    SSH will tunnel through the selected node before connecting to this host.
                  </p>
                )}
              </div>
            </div>

            {/* Tags section */}
            <div className="pb-5">
              <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-quaternary)]">
                Organization
              </h3>
              <div>
                <label className={labelCls}>Tags</label>
                <input
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="gpu, production, ml-team"
                  className={inputCls}
                />
                <p className="mt-1.5 text-[11px] text-[var(--text-tertiary)]">
                  Comma-separated tags for filtering and grouping.
                </p>
              </div>
            </div>

            {/* Spacer */}
            <div className="flex-1" />
          </form>

          {/* Footer — sticky */}
          <div className="flex items-center justify-end gap-3 border-t border-[var(--border-subtle)] px-6 py-4">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-2.5 text-[13px] font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              onClick={handleSubmit}
              className="rounded-lg bg-[var(--green)] px-5 py-2.5 text-[13px] font-semibold text-black transition-all duration-200 hover:bg-[var(--green-light)] disabled:opacity-30"
            >
              {isPending
                ? isEdit ? "Saving..." : "Creating..."
                : isEdit ? "Save Changes" : "Create Node"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
