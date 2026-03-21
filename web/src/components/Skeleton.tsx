import clsx from "clsx";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return <div className={clsx("skeleton", className)} />;
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-5">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-8 w-8 rounded-lg" />
      </div>
      <Skeleton className="mt-4 h-8 w-16" />
    </div>
  );
}

export function NodeCardSkeleton() {
  return (
    <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-5">
      <div className="flex items-center gap-3">
        <Skeleton className="h-2 w-2 rounded-full" />
        <Skeleton className="h-4 w-28" />
      </div>
      <Skeleton className="mt-3 h-3 w-36" />
      <Skeleton className="mt-4 h-3 w-20" />
    </div>
  );
}

export function CommandSkeleton() {
  return (
    <div className="border-b border-[var(--border-subtle)] px-5 py-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-3 w-[60px]" />
        <Skeleton className="h-3 w-3" />
        <Skeleton className="h-3 w-[40%]" />
        <div className="flex-1" />
        <Skeleton className="h-3 w-6" />
        <Skeleton className="h-3 w-10" />
      </div>
    </div>
  );
}

export function RuleSkeleton() {
  return (
    <div className="flex items-center gap-4 border-b border-[var(--border-subtle)] px-5 py-3">
      <Skeleton className="h-5 w-32" />
      <Skeleton className="h-5 w-16 rounded-full" />
      <Skeleton className="h-4 w-48" />
      <div className="flex-1" />
      <Skeleton className="h-4 w-8" />
    </div>
  );
}

export function RecentCommandSkeleton() {
  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <Skeleton className="h-[6px] w-[6px] rounded-full" />
      <Skeleton className="h-3 w-16" />
      <Skeleton className="h-3 w-[45%]" />
      <div className="flex-1" />
      <Skeleton className="h-3 w-6" />
    </div>
  );
}
