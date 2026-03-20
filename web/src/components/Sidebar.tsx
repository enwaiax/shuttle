import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Server,
  Shield,
  Terminal,
  ScrollText,
  Settings,
} from "lucide-react";
import clsx from "clsx";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/nodes", label: "Nodes", icon: Server },
  { to: "/rules", label: "Security Rules", icon: Shield },
  { to: "/sessions", label: "Sessions", icon: Terminal },
  { to: "/logs", label: "Command Logs", icon: ScrollText },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export default function Sidebar() {
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

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 px-3">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-all",
                isActive
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:bg-gray-200/50 hover:text-gray-700",
              )
            }
          >
            <Icon size={16} strokeWidth={1.8} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
