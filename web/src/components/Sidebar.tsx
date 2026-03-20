import { useEffect } from "react";
import { NavLink, useParams, useNavigate } from "react-router-dom";
import { Shield, Settings, Plus } from "lucide-react";
import clsx from "clsx";
import { useNodes } from "../api/client";

export default function Sidebar() {
  const { data: nodes } = useNodes();
  const { nodeId } = useParams<{ nodeId?: string }>();
  const navigate = useNavigate();

  useEffect(() => {
    if (!nodeId && nodes && nodes.length > 0) {
      navigate(`/activity/${nodes[0].id}`, { replace: true });
    }
  }, [nodeId, nodes, navigate]);

  return (
    <aside className="flex w-[200px] flex-col border-r border-[#1a1a1a] bg-[#0a0a0a]">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-4 py-4">
        <div className="flex h-6 w-6 items-center justify-center rounded border border-[#222] bg-[#111]">
          <span
            className="text-[11px] font-semibold text-[#ededed]"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            S
          </span>
        </div>
        <span className="text-[13px] font-medium tracking-[-0.01em] text-[#999]">
          Shuttle
        </span>
      </div>

      <nav className="flex-1 px-2">
        {/* Section label */}
        <p className="mb-1.5 mt-2 px-2 text-[10px] font-medium uppercase tracking-[0.08em] text-[#444]">
          Nodes
        </p>

        {nodes?.map((node) => (
          <NavLink
            key={node.id}
            to={`/activity/${node.id}`}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-2 rounded-md px-2 py-[5px] text-[13px] transition-colors",
                isActive
                  ? "bg-[#161616] text-[#ededed]"
                  : "text-[#666] hover:bg-[#111] hover:text-[#999]",
              )
            }
          >
            <span
              className={clsx(
                "h-[6px] w-[6px] rounded-full",
                node.status === "active" ? "bg-[#0f0]" : "bg-[#333]",
              )}
              style={
                node.status === "active"
                  ? { boxShadow: "0 0 4px rgba(0,255,0,0.3)" }
                  : undefined
              }
            />
            <span className="truncate">{node.name}</span>
          </NavLink>
        ))}

        <NavLink
          to="/nodes"
          className={({ isActive }) =>
            clsx(
              "mt-1 flex items-center gap-2 rounded-md px-2 py-[5px] text-[13px] transition-colors",
              isActive
                ? "bg-[#161616] text-[#ededed]"
                : "text-[#333] hover:bg-[#111] hover:text-[#666]",
            )
          }
        >
          <Plus size={13} strokeWidth={1.5} />
          Add node
        </NavLink>

        {/* Divider */}
        <div className="my-4 border-t border-[#1a1a1a]" />

        <NavLink
          to="/rules"
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-2 rounded-md px-2 py-[5px] text-[13px] transition-colors",
              isActive
                ? "bg-[#161616] text-[#ededed]"
                : "text-[#666] hover:bg-[#111] hover:text-[#999]",
            )
          }
        >
          <Shield size={13} strokeWidth={1.5} />
          Rules
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-2 rounded-md px-2 py-[5px] text-[13px] transition-colors",
              isActive
                ? "bg-[#161616] text-[#ededed]"
                : "text-[#666] hover:bg-[#111] hover:text-[#999]",
            )
          }
        >
          <Settings size={13} strokeWidth={1.5} />
          Settings
        </NavLink>
      </nav>

      {/* Status bar */}
      <div className="border-t border-[#1a1a1a] px-4 py-3">
        <p className="text-[11px] text-[#333]">
          {nodes?.length ?? 0} node{nodes?.length !== 1 ? "s" : ""} connected
        </p>
      </div>
    </aside>
  );
}
