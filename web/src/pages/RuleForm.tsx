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
  "focus-ring w-full rounded-xl border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-2.5 text-[13px] text-[var(--text-primary)] outline-none transition-all duration-200 placeholder:text-[var(--text-muted)] hover:border-[var(--border-strong)]";

const labelCls = "mb-2 block text-[12px] font-medium text-[var(--text-secondary)]";

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

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/70 backdrop-blur-md data-[state=open]:animate-fade-in" />
        <Dialog.Content className="animate-scale-in fixed left-1/2 top-1/2 w-full max-w-md rounded-2xl border border-[var(--border-default)] bg-[var(--bg-elevated)] p-6 shadow-2xl focus:outline-none">
          <div className="flex items-start justify-between">
            <Dialog.Title className="text-[15px] font-semibold text-[var(--text-primary)]">
              Add Rule
            </Dialog.Title>
            <Dialog.Close className="rounded-lg p-1.5 text-[var(--text-quaternary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]">
              <X size={14} />
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <div>
              <label className={labelCls}>Pattern (regex)</label>
              <input
                required
                value={pattern}
                onChange={(e) => setPattern(e.target.value)}
                placeholder="sudo .*"
                className={inputCls}
                style={{ fontFamily: "var(--font-mono)" }}
              />
            </div>
            <div>
              <label className={labelCls}>Security Level</label>
              <div className="grid grid-cols-4 gap-2">
                {levels.map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => setLevel(l)}
                    className={`rounded-lg border px-3 py-2 text-[12px] font-semibold capitalize transition-all duration-200 ${
                      level === l
                        ? l === "block"
                          ? "border-[var(--red)]/30 bg-[var(--red-subtle)] text-[var(--red)]"
                          : l === "confirm"
                            ? "border-[var(--orange)]/30 bg-[var(--orange-subtle)] text-[var(--orange)]"
                            : l === "warn"
                              ? "border-[var(--yellow)]/30 bg-[var(--yellow-subtle)] text-[var(--yellow)]"
                              : "border-[var(--green)]/30 bg-[var(--green-subtle)] text-[var(--green)]"
                        : "border-[var(--border-default)] bg-[var(--bg-tertiary)] text-[var(--text-quaternary)] hover:border-[var(--border-strong)]"
                    }`}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className={labelCls}>Description</label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Optional description"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Priority</label>
              <input
                required
                type="number"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className={inputCls}
                style={{ fontFamily: "var(--font-mono)" }}
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
                {create.isPending ? "Creating…" : "Create Rule"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
