import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useCreateRule } from "../api/client";

interface RuleFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const levels = ["block", "confirm", "warn", "allow"] as const;

export default function RuleForm({ open, onOpenChange }: RuleFormProps) {
  const [pattern, setPattern] = useState("");
  const [level, setLevel] = useState<string>("block");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("100");

  const create = useCreateRule();

  function reset() {
    setPattern("");
    setLevel("block");
    setDescription("");
    setPriority("100");
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    create.mutate(
      {
        pattern,
        level,
        description: description || undefined,
        priority: Number(priority),
      },
      {
        onSuccess: () => {
          reset();
          onOpenChange(false);
        },
      },
    );
  }

  const inputCls =
    "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-gray-200 bg-white p-6 shadow-lg focus:outline-none">
          <div className="flex items-start justify-between">
            <Dialog.Title className="text-base font-semibold text-gray-900">
              Add Security Rule
            </Dialog.Title>
            <Dialog.Close className="rounded-md p-1 text-gray-400 hover:text-gray-600">
              <X size={16} />
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Pattern
              </label>
              <input
                required
                value={pattern}
                onChange={(e) => setPattern(e.target.value)}
                placeholder="rm -rf *"
                className={inputCls}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Level
              </label>
              <select
                value={level}
                onChange={(e) => setLevel(e.target.value)}
                className={inputCls}
              >
                {levels.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Description
              </label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                className={inputCls}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Priority
              </label>
              <input
                required
                type="number"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className={inputCls}
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Dialog.Close className="rounded-lg border border-gray-200 bg-white px-3.5 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50">
                Cancel
              </Dialog.Close>
              <button
                type="submit"
                disabled={create.isPending}
                className="rounded-lg bg-blue-600 px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {create.isPending ? "Creating..." : "Create"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
