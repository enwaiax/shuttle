import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useCreateNode } from "../api/client";

interface NodeFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const inputCls =
  "focus-ring w-full rounded-xl border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-2.5 text-[13px] text-[var(--text-primary)] outline-none transition-all duration-200 placeholder:text-[var(--text-muted)] hover:border-[var(--border-strong)]";

const labelCls = "mb-2 block text-[12px] font-medium text-[var(--text-secondary)]";

export default function NodeForm({ open, onOpenChange }: NodeFormProps) {
  const [name, setName] = useState("");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("22");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const create = useCreateNode();

  function reset() {
    setName("");
    setHost("");
    setPort("22");
    setUsername("");
    setPassword("");
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    create.mutate(
      {
        name,
        host,
        port: Number(port),
        username,
        auth_type: "password",
        credential: password,
      },
      {
        onSuccess: () => {
          reset();
          onOpenChange(false);
        },
      },
    );
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/70 backdrop-blur-md data-[state=open]:animate-fade-in" />
        <Dialog.Content className="animate-scale-in fixed left-1/2 top-1/2 w-full max-w-md rounded-2xl border border-[var(--border-default)] bg-[var(--bg-elevated)] p-6 shadow-2xl focus:outline-none">
          <div className="flex items-start justify-between">
            <Dialog.Title className="text-[15px] font-semibold text-[var(--text-primary)]">
              Add Node
            </Dialog.Title>
            <Dialog.Close className="rounded-lg p-1.5 text-[var(--text-quaternary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]">
              <X size={14} />
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <div>
              <label className={labelCls}>Name</label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="my-server"
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
                  placeholder="192.168.1.100"
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
            <div>
              <label className={labelCls}>Password</label>
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputCls}
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Dialog.Close className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-2.5 text-[13px] font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]">
                Cancel
              </Dialog.Close>
              <button
                type="submit"
                disabled={create.isPending}
                className="rounded-xl bg-[var(--green)] px-5 py-2.5 text-[13px] font-semibold text-black transition-all duration-200 hover:bg-[var(--green-light)] disabled:opacity-30"
              >
                {create.isPending ? "Creating…" : "Create Node"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
