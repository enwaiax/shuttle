import clsx from "clsx";

const colorMap: Record<string, string> = {
  block: "bg-[var(--red-subtle)] text-[var(--red)]",
  confirm: "bg-[var(--orange-subtle)] text-[var(--orange)]",
  warn: "bg-[var(--yellow-subtle)] text-[var(--yellow)]",
  allow: "bg-[var(--success-subtle)] text-[var(--success)]",
  active: "bg-[var(--green-subtle)] text-[var(--green)]",
  online: "bg-[var(--green-subtle)] text-[var(--green)]",
  closed: "bg-[var(--bg-hover)] text-[var(--text-quaternary)]",
  offline: "bg-[var(--red-subtle)] text-[var(--red)]",
};

const fallback = "bg-[var(--bg-hover)] text-[var(--text-tertiary)]";

interface BadgeProps {
  value: string;
  className?: string;
}

export default function Badge({ value, className }: BadgeProps) {
  const colors = colorMap[value.toLowerCase()] ?? fallback;
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-[3px] text-[10px] font-semibold uppercase tracking-wide",
        colors,
        className,
      )}
    >
      {value}
    </span>
  );
}
