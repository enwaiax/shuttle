import { NavLink, useLocation } from "react-router-dom";
import { Shield, Settings, Server, Sun, Moon } from "lucide-react";
import clsx from "clsx";
import { useApp } from "../hooks/AppContext";

const navItemCls = (active: boolean) =>
  clsx(
    "group flex items-center gap-2.5 rounded-lg px-3 py-[7px] text-[13px] font-medium transition-all duration-200",
    active
      ? "bg-[var(--green-subtle)] text-[var(--green)]"
      : "text-[var(--text-tertiary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]",
  );

export default function Sidebar() {
  const { pathname } = useLocation();
  const { theme, toggleTheme, recentNodes } = useApp();
  const isNodesActive = pathname === "/" || pathname.startsWith("/nodes");

  return (
    <aside
      className="select-none-chrome flex w-[220px] shrink-0 flex-col border-r border-[var(--border-sidebar)] bg-[var(--bg-sidebar)]"
      aria-label="Main navigation"
    >
      {/* Brand + Theme toggle */}
      <div className="flex items-center justify-between px-5 py-4">
        <NavLink
          to="/"
          className="flex items-center gap-3 transition-opacity hover:opacity-80"
          aria-label="Shuttle — go to nodes"
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
        <button
          onClick={toggleTheme}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          className="rounded-lg p-2 text-[var(--text-quaternary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
        >
          {theme === "dark" ? (
            <Sun size={15} strokeWidth={1.8} />
          ) : (
            <Moon size={15} strokeWidth={1.8} />
          )}
        </button>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3" role="navigation">
        <NavLink to="/" end className={() => navItemCls(isNodesActive)}>
          <Server size={14} strokeWidth={1.8} />
          Nodes
        </NavLink>

        {/* Recent nodes */}
        {recentNodes.length > 0 && (
          <>
            <div className="!mt-4 !mb-1.5 px-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-quaternary)]">
                Recent
              </p>
            </div>
            {recentNodes.map((node) => (
              <NavLink
                key={node.id}
                to={`/nodes/${node.id}`}
                aria-label={`${node.name} — ${node.status === "active" ? "online" : "offline"}`}
                className={({ isActive }) =>
                  clsx(
                    "group flex items-center gap-2.5 rounded-lg px-3 py-[6px] text-[12px] transition-all duration-200",
                    isActive
                      ? "bg-[var(--bg-elevated)] text-[var(--text-primary)]"
                      : "text-[var(--text-tertiary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]",
                  )
                }
              >
                <span
                  className={clsx(
                    "h-[6px] w-[6px] shrink-0 rounded-full",
                    node.status === "active"
                      ? "bg-[var(--green)] animate-pulse-green"
                      : "bg-[var(--text-muted)]",
                  )}
                  aria-hidden="true"
                />
                <span className="truncate">{node.name}</span>
              </NavLink>
            ))}
          </>
        )}

        <div className="!my-4 border-t border-[var(--border-subtle)]" />

        <NavLink to="/rules" className={({ isActive }) => navItemCls(isActive)}>
          <Shield size={14} strokeWidth={1.8} />
          Rules
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => navItemCls(isActive)}>
          <Settings size={14} strokeWidth={1.8} />
          Settings
        </NavLink>
      </nav>

      {/* Footer */}
      <div className="border-t border-[var(--border-subtle)] px-5 py-3">
        <p className="text-[10px] text-[var(--text-muted)]">Shuttle MCP v2</p>
      </div>
    </aside>
  );
}
