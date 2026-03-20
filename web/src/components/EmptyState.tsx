import { type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
}

export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="animate-fade-in flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--border-default)] bg-[var(--bg-elevated)]">
        <Icon size={24} className="text-[var(--text-quaternary)]" strokeWidth={1.5} />
      </div>
      <h3 className="text-[15px] font-semibold text-[var(--text-primary)]">{title}</h3>
      <p className="mt-2 max-w-sm text-[13px] leading-relaxed text-[var(--text-tertiary)]">
        {description}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
