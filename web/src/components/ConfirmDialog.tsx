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
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-[#222] bg-[#111] p-6 shadow-2xl focus:outline-none">
          <div className="flex items-start justify-between">
            <Dialog.Title className="text-[14px] font-medium text-[#ededed]">
              {title}
            </Dialog.Title>
            <Dialog.Close className="rounded-md p-1 text-[#555] hover:text-[#999]">
              <X size={14} />
            </Dialog.Close>
          </div>
          <Dialog.Description className="mt-2 text-[13px] text-[#666]">
            {description}
          </Dialog.Description>
          <div className="mt-6 flex justify-end gap-3">
            <Dialog.Close className="rounded-md border border-[#222] bg-[#161616] px-3 py-1.5 text-[13px] font-medium text-[#999] hover:bg-[#1a1a1a]">
              Cancel
            </Dialog.Close>
            <button
              onClick={() => {
                onConfirm();
                onOpenChange(false);
              }}
              className={clsx(
                "rounded-md px-3 py-1.5 text-[13px] font-medium",
                variant === "danger"
                  ? "bg-[#ff4444] text-white hover:bg-[#e63e3e]"
                  : "bg-[#ededed] text-[#0a0a0a] hover:opacity-90",
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
