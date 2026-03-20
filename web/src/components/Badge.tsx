import clsx from "clsx";

const colorMap: Record<string, string> = {
  block: "bg-[#ff0000]/10 text-[#ff4444]",
  confirm: "bg-[#ff9500]/10 text-[#ff9500]",
  warn: "bg-[#ffd60a]/8 text-[#ffd60a]",
  allow: "bg-[#30d158]/10 text-[#30d158]",
  active: "bg-[#30d158]/10 text-[#30d158]",
  online: "bg-[#30d158]/10 text-[#30d158]",
  closed: "bg-[#333]/50 text-[#666]",
  offline: "bg-[#ff4444]/10 text-[#ff4444]",
};

const fallback = "bg-[#222] text-[#666]";

interface BadgeProps {
  value: string;
  className?: string;
}

export default function Badge({ value, className }: BadgeProps) {
  const colors = colorMap[value.toLowerCase()] ?? fallback;
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
        colors,
        className,
      )}
    >
      {value}
    </span>
  );
}
