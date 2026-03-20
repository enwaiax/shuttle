import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useCreateNode } from "../api/client";

interface NodeFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const inputCls =
  "w-full rounded-md border border-[#222] bg-[#0e0e0e] px-3 py-2 text-[13px] text-[#ededed] outline-none placeholder:text-[#444] focus:border-[#444]";

export default function NodeForm({ open, onOpenChange }: NodeFormProps) {
  const [name, setName] = useState("");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("22");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const create = useCreateNode();

  function reset() { setName(""); setHost(""); setPort("22"); setUsername(""); setPassword(""); }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    create.mutate(
      { name, host, port: Number(port), username, auth_type: "password", credential: password },
      { onSuccess: () => { reset(); onOpenChange(false); } },
    );
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-[#222] bg-[#111] p-6 shadow-2xl focus:outline-none">
          <div className="flex items-start justify-between">
            <Dialog.Title className="text-[14px] font-medium text-[#ededed]">Add Node</Dialog.Title>
            <Dialog.Close className="rounded-md p-1 text-[#555] hover:text-[#999]">
              <X size={14} />
            </Dialog.Close>
          </div>
          <form onSubmit={handleSubmit} className="mt-4 space-y-3">
            <div>
              <label className="mb-1 block text-[11px] font-medium text-[#666]">Name</label>
              <input required value={name} onChange={(e) => setName(e.target.value)} placeholder="my-server" className={inputCls} />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label className="mb-1 block text-[11px] font-medium text-[#666]">Host</label>
                <input required value={host} onChange={(e) => setHost(e.target.value)} placeholder="192.168.1.100" className={inputCls} />
              </div>
              <div>
                <label className="mb-1 block text-[11px] font-medium text-[#666]">Port</label>
                <input required type="number" value={port} onChange={(e) => setPort(e.target.value)} className={inputCls} />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-medium text-[#666]">Username</label>
              <input required value={username} onChange={(e) => setUsername(e.target.value)} placeholder="root" className={inputCls} />
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-medium text-[#666]">Password</label>
              <input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls} />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Dialog.Close className="rounded-md border border-[#222] bg-[#161616] px-3 py-1.5 text-[13px] font-medium text-[#999] hover:bg-[#1a1a1a]">
                Cancel
              </Dialog.Close>
              <button type="submit" disabled={create.isPending} className="rounded-md bg-[#ededed] px-3 py-1.5 text-[13px] font-medium text-[#0a0a0a] hover:opacity-90 disabled:opacity-30">
                {create.isPending ? "Creating…" : "Create"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
