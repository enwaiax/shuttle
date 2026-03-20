import { NavLink } from "react-router-dom";
import { Terminal, Shield, Settings, Plus, Server } from "lucide-react";
import clsx from "clsx";
import { useNodes } from "../api/client";

function linkClass({ isActive }: { isActive: boolean }) {
  return clsx(
    "flex items-center gap-2.5 rounded-md px-3 py-1.5 text-[13px] font-medium transition-all",
    isActive
      ? "bg-zinc-800 text-zinc-100"
      : "text-zinc-500 hover:bg-zinc-800/50 hover:text-zinc-300",
  );
}

export default function Sidebar() {
  const { data: nodes } = useNodes();

  return (
    <aside className="flex w-52 flex-col border-r border-zinc-800/80 bg-zinc-900">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-emerald-400 to-cyan-500 text-xs font-bold text-zinc-900">
          S
        </div>
        <span className="text-sm font-semibold tracking-tight text-zinc-200">
          Shuttle
        </span>
      </div>

      <nav className="flex-1 space-y-0.5 px-2">
        {/* All Activity */}
        <NavLink to="/activity" end className={linkClass}>
          <Terminal size={14} strokeWidth={1.8} />
          All Activity
        </NavLink>

        {/* Nodes section */}
        <div className="my-3 border-t border-zinc-800/60" />
        <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
          Nodes
        </p>

        {nodes?.map((node) => (
          <NavLink
            key={node.id}
            to={`/activity/${node.id}`}
            className={linkClass}
          >
            <span
              className={clsx(
                "inline-block h-1.5 w-1.5 rounded-full",
                node.status === "active" ? "bg-emerald-400" : "bg-zinc-600",
              )}
            />
            <span className="truncate">{node.name}</span>
          </NavLink>
        ))}

        <NavLink to="/nodes" className={linkClass}>
          <Plus size={14} strokeWidth={1.8} />
          <span className="text-zinc-600">Add Node</span>
        </NavLink>

        {/* Bottom links */}
        <div className="my-3 border-t border-zinc-800/60" />
        <NavLink to="/rules" className={linkClass}>
          <Shield size={14} strokeWidth={1.8} />
          Security Rules
        </NavLink>
        <NavLink to="/settings" className={linkClass}>
          <Settings size={14} strokeWidth={1.8} />
          Settings
        </NavLink>
      </nav>

      {/* Footer */}
      <div className="border-t border-zinc-800/60 px-4 py-3">
        <div className="flex items-center gap-2 text-[11px] text-zinc-600">
          <Server size={11} />
          <span>{nodes?.length ?? 0} nodes</span>
        </div>
      </div>
    </aside>
  );
}
