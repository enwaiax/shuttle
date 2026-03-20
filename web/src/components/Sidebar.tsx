import { NavLink } from "react-router-dom";
import { Activity, Shield, Settings, Plus } from "lucide-react";
import clsx from "clsx";
import { useNodes } from "../api/client";

function linkClass({ isActive }: { isActive: boolean }) {
  return clsx(
    "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-all",
    isActive
      ? "bg-white text-gray-900 shadow-sm"
      : "text-gray-500 hover:bg-gray-200/50 hover:text-gray-700",
  );
}

export default function Sidebar() {
  const { data: nodes } = useNodes();

  return (
    <aside className="flex w-56 flex-col border-r border-gray-200/60 bg-gray-100/70 backdrop-blur-xl">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-sm font-bold text-white shadow-sm">
          S
        </div>
        <span className="text-[15px] font-semibold tracking-tight text-gray-900">
          Shuttle
        </span>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {/* All Activity */}
        <NavLink to="/activity" end className={linkClass}>
          <Activity size={16} strokeWidth={1.8} />
          All Activity
        </NavLink>

        {/* Divider */}
        <div className="my-2 border-t border-gray-200/60" />

        {/* Nodes section */}
        <p className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
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
                "inline-block h-2 w-2 rounded-full",
                node.status === "online" ? "bg-green-500" : "bg-gray-400",
              )}
            />
            <span className="truncate">{node.name}</span>
          </NavLink>
        ))}

        <NavLink to="/nodes" className={linkClass}>
          <Plus size={16} strokeWidth={1.8} />
          Add Node
        </NavLink>

        {/* Divider */}
        <div className="my-2 border-t border-gray-200/60" />

        {/* Bottom links */}
        <NavLink to="/rules" className={linkClass}>
          <Shield size={16} strokeWidth={1.8} />
          Security Rules
        </NavLink>
        <NavLink to="/settings" className={linkClass}>
          <Settings size={16} strokeWidth={1.8} />
          Settings
        </NavLink>
      </nav>
    </aside>
  );
}
