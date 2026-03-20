import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useCreateRule } from "../api/client";

interface RuleFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const levels = ["block", "confirm", "warn", "allow"] as const;

const inputCls =
  "w-full rounded-md border border-[#222] bg-[#0e0e0e] px-3 py-2 text-[13px] text-[#ededed] outline-none placeholder:text-[#444] focus:border-[#444]";

export default function RuleForm({ open, onOpenChange }: RuleFormProps) {
  const [pattern, setPattern] = useState("");
  const [level, setLevel] = useState<string>("block");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("100");
  const create = useCreateRule();

  function reset() { setPattern(""); setLevel("block"); setDescription(""); setPriority("100"); }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    create.mutate(
      { pattern, level, description: description || undefined, priority: Number(priority) },
      { onSuccess: () => { reset(); onOpenChange(false); } },
    );
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-[#222] bg-[#111] p-6 shadow-2xl focus:outline-none">
          <div className="flex items-start justify-between">
            <Dialog.Title className="text-[14px] font-medium text-[#ededed]">Add Rule</Dialog.Title>
            <Dialog.Close className="rounded-md p-1 text-[#555] hover:text-[#999]">
              <X size={14} />
            </Dialog.Close>
          </div>
          <form onSubmit={handleSubmit} className="mt-4 space-y-3">
            <div>
              <label className="mb-1 block text-[11px] font-medium text-[#666]">Pattern (regex)</label>
              <input required value={pattern} onChange={(e) => setPattern(e.target.value)} placeholder="sudo .*" className={inputCls} style={{ fontFamily: "'JetBrains Mono', monospace" }} />
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-medium text-[#666]">Level</label>
              <select value={level} onChange={(e) => setLevel(e.target.value)} className={inputCls}>
                {levels.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-medium text-[#666]">Description</label>
              <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional" className={inputCls} />
            </div>
            <div>
              <label className="mb-1 block text-[11px] font-medium text-[#666]">Priority</label>
              <input required type="number" value={priority} onChange={(e) => setPriority(e.target.value)} className={inputCls} />
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
