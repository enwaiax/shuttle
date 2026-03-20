import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import clsx from "clsx";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  variant?: "default" | "danger";
  onConfirm: () => void;
}

export default function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  variant = "default",
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/70 backdrop-blur-md data-[state=open]:animate-fade-in" />
        <Dialog.Content className="animate-scale-in fixed left-1/2 top-1/2 w-full max-w-md rounded-2xl border border-[var(--border-default)] bg-[var(--bg-elevated)] p-6 shadow-2xl focus:outline-none">
          <div className="flex items-start justify-between">
            <Dialog.Title className="text-[15px] font-semibold text-[var(--text-primary)]">
              {title}
            </Dialog.Title>
            <Dialog.Close className="rounded-lg p-1.5 text-[var(--text-quaternary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]">
              <X size={14} />
            </Dialog.Close>
          </div>
          <Dialog.Description className="mt-3 text-[13px] leading-relaxed text-[var(--text-tertiary)]">
            {description}
          </Dialog.Description>
          <div className="mt-6 flex justify-end gap-3">
            <Dialog.Close className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-2 text-[13px] font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]">
              Cancel
            </Dialog.Close>
            <button
              onClick={() => {
                onConfirm();
                onOpenChange(false);
              }}
              className={clsx(
                "rounded-lg px-4 py-2 text-[13px] font-semibold transition-all duration-200",
                variant === "danger"
                  ? "bg-[var(--red)] text-white hover:brightness-110"
                  : "bg-[var(--green)] text-black hover:bg-[var(--green-light)]",
              )}
            >
              {confirmLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
