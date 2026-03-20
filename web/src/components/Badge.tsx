import clsx from "clsx";

const colorMap: Record<string, string> = {
  block: "bg-red-50 text-red-700 ring-red-600/20",
  confirm: "bg-amber-50 text-amber-700 ring-amber-600/20",
  warn: "bg-yellow-50 text-yellow-700 ring-yellow-600/20",
  allow: "bg-green-50 text-green-700 ring-green-600/20",
  active: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  online: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  closed: "bg-gray-50 text-gray-600 ring-gray-500/20",
  offline: "bg-gray-50 text-gray-600 ring-gray-500/20",
};

const fallback = "bg-gray-50 text-gray-600 ring-gray-500/20";

interface BadgeProps {
  value: string;
  className?: string;
}

export default function Badge({ value, className }: BadgeProps) {
  const colors = colorMap[value.toLowerCase()] ?? fallback;
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        colors,
        className,
      )}
    >
      {value}
    </span>
  );
}
