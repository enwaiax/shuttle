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
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 rounded-full bg-[#161616] p-3">
        <Icon size={24} className="text-[#444]" strokeWidth={1.5} />
      </div>
      <h3 className="text-[13px] font-medium text-[#ededed]">{title}</h3>
      <p className="mt-1 max-w-sm text-[12px] text-[#555]">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
