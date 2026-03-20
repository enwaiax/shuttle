import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Server, Terminal, Plus } from "lucide-react";
import { useNodes, useStats } from "../api/client";
import type { NodeResponse } from "../types";
import NodeForm from "./NodeForm";

function NodeCard({ node, onClick }: { node: NodeResponse; onClick: () => void }) {
  const isActive = node.status === "active";

  return (
    <button
      onClick={onClick}
      className="group flex flex-col rounded-lg border border-[#1a1a1a] bg-[#0e0e0e] p-4 text-left transition-colors hover:border-[#333] hover:bg-[#111]"
    >
      <div className="flex items-center gap-2.5">
        <span
          className={`h-2 w-2 rounded-full ${isActive ? "bg-[#0f0]" : "bg-[#333]"}`}
          style={isActive ? { boxShadow: "0 0 4px rgba(0,255,0,0.3)" } : undefined}
        />
        <span className="text-[14px] font-medium text-[#ededed]">{node.name}</span>
      </div>
      <p
        className="mt-2 text-[12px] text-[#555]"
        style={{ fontFamily: "'JetBrains Mono', monospace" }}
      >
        {node.username}@{node.host}:{node.port}
      </p>
      <div className="mt-3 flex items-center gap-1 text-[11px] text-[#444] group-hover:text-[#666]">
        <Terminal size={11} />
        <span>View activity →</span>
      </div>
    </button>
  );
}

export default function Overview() {
  const { data: nodes = [] } = useNodes();
  const { data: stats } = useStats();
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="flex h-full flex-col bg-[#0a0a0a]">
      {/* Header */}
      <div className="border-b border-[#1a1a1a] px-8 py-6">
        <h1 className="text-[15px] font-medium text-[#ededed]">Shuttle</h1>
        <p className="mt-1 text-[13px] text-[#555]">
          {stats
            ? `${stats.node_count} nodes · ${stats.total_commands} commands executed`
            : "Loading…"}
        </p>
      </div>

      {/* Node grid */}
      <div className="flex-1 overflow-y-auto px-8 py-6">
        {nodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="mb-4 rounded-full bg-[#161616] p-3">
              <Server size={24} className="text-[#444]" strokeWidth={1.5} />
            </div>
            <p className="text-[13px] font-medium text-[#ededed]">No nodes configured</p>
            <p className="mt-1 text-[12px] text-[#555]">
              Add a node to start monitoring SSH activity
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="mt-4 rounded-md bg-[#ededed] px-3 py-1.5 text-[13px] font-medium text-[#0a0a0a] hover:opacity-90"
            >
              Add Node
            </button>
          </div>
        ) : (
          <>
            <p className="mb-4 text-[11px] font-medium uppercase tracking-[0.08em] text-[#444]">
              Nodes
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {nodes.map((node) => (
                <NodeCard
                  key={node.id}
                  node={node}
                  onClick={() => navigate(`/activity/${node.id}`)}
                />
              ))}
              {/* Add node card */}
              <button
                onClick={() => setShowForm(true)}
                className="flex flex-col items-center justify-center rounded-lg border border-dashed border-[#222] p-4 text-[#444] transition-colors hover:border-[#444] hover:text-[#666]"
              >
                <Plus size={16} />
                <span className="mt-1 text-[12px]">Add node</span>
              </button>
            </div>
          </>
        )}
      </div>

      <NodeForm open={showForm} onOpenChange={setShowForm} />
    </div>
  );
}
