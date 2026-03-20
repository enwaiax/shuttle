import { NavLink } from "react-router-dom";
import { Shield, Settings, Plus, LayoutGrid } from "lucide-react";
import clsx from "clsx";
import { useNodes } from "../api/client";

const navItemCls = (isActive: boolean) =>
  clsx(
    "group flex items-center gap-2.5 rounded-lg px-3 py-[7px] text-[13px] font-medium transition-all duration-200",
    isActive
      ? "bg-[var(--green-subtle)] text-[var(--green)]"
      : "text-[var(--text-tertiary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]",
  );

export default function Sidebar() {
  const { data: nodes } = useNodes();

  return (
    <aside className="flex w-[220px] shrink-0 flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
      {/* Brand */}
      <NavLink
        to="/"
        className="flex items-center gap-3 px-5 py-5 transition-opacity hover:opacity-80"
      >
        <div className="flex h-7 w-7 items-center justify-center rounded-md border border-[var(--green)]/30 bg-[var(--green-subtle)]">
          <span
            className="text-[12px] font-bold text-[var(--green)]"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            S
          </span>
        </div>
        <span className="text-[14px] font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
          Shuttle
        </span>
      </NavLink>

      <nav className="flex-1 space-y-0.5 px-3">
        {/* Overview */}
        <NavLink to="/" end className={({ isActive }) => navItemCls(isActive)}>
          <LayoutGrid size={14} strokeWidth={1.8} />
          Overview
        </NavLink>

        {/* Nodes section */}
        <div className="!mt-5 !mb-2 flex items-center justify-between px-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-quaternary)]">
            Nodes
          </p>
          <span className="text-[10px] tabular-nums text-[var(--text-muted)]">
            {nodes?.length ?? 0}
          </span>
        </div>

        {nodes?.map((node) => (
          <NavLink
            key={node.id}
            to={`/activity/${node.id}`}
            className={({ isActive }) =>
              clsx(
                "group flex items-center gap-2.5 rounded-lg px-3 py-[7px] text-[13px] transition-all duration-200",
                isActive
                  ? "bg-[var(--bg-elevated)] text-[var(--text-primary)]"
                  : "text-[var(--text-tertiary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]",
              )
            }
          >
            <span
              className={clsx(
                "h-[7px] w-[7px] shrink-0 rounded-full transition-all",
                node.status === "active"
                  ? "bg-[var(--green)] animate-pulse-green"
                  : "bg-[var(--text-muted)]",
              )}
            />
            <span className="truncate">{node.name}</span>
          </NavLink>
        ))}

        <NavLink
          to="/"
          end={false}
          className="mt-1 flex items-center gap-2.5 rounded-lg border border-dashed border-[var(--border-default)] px-3 py-[6px] text-[12px] text-[var(--text-quaternary)] transition-all duration-200 hover:border-[var(--green)]/30 hover:text-[var(--green)]"
        >
          <Plus size={12} strokeWidth={2} />
          Add node
        </NavLink>

        {/* Divider */}
        <div className="!my-4 border-t border-[var(--border-subtle)]" />

        <NavLink
          to="/rules"
          className={({ isActive }) => navItemCls(isActive)}
        >
          <Shield size={14} strokeWidth={1.8} />
          Rules
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) => navItemCls(isActive)}
        >
          <Settings size={14} strokeWidth={1.8} />
          Settings
        </NavLink>
      </nav>

      {/* Footer */}
      <div className="border-t border-[var(--border-subtle)] px-5 py-3">
        <p className="text-[10px] text-[var(--text-muted)]">
          Shuttle MCP v2
        </p>
      </div>
    </aside>
  );
}
