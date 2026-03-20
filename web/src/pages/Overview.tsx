import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Server, Terminal, Plus, Activity, Cpu, Command } from "lucide-react";
import { useNodes, useStats } from "../api/client";
import type { NodeResponse } from "../types";
import NodeForm from "./NodeForm";

function StatCard({
  label,
  value,
  icon: Icon,
  delay,
}: {
  label: string;
  value: number | undefined;
  icon: typeof Server;
  delay: string;
}) {
  return (
    <div
      className="animate-slide-up group rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-5 transition-all duration-300 hover:border-[var(--green)]/20 hover:shadow-[0_0_30px_rgba(118,185,0,0.05)]"
      style={{ animationDelay: delay }}
    >
      <div className="flex items-center justify-between">
        <p className="text-[12px] font-medium text-[var(--text-tertiary)]">{label}</p>
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--green-subtle)] transition-colors group-hover:bg-[var(--green-subtle)]">
          <Icon size={15} className="text-[var(--green)]" strokeWidth={1.8} />
        </div>
      </div>
      <p className="mt-3 text-[28px] font-bold tabular-nums tracking-[-0.04em] text-[var(--text-primary)]">
        {value ?? "—"}
      </p>
    </div>
  );
}

function NodeCard({
  node,
  onClick,
  index,
}: {
  node: NodeResponse;
  onClick: () => void;
  index: number;
}) {
  const isActive = node.status === "active";

  return (
    <button
      onClick={onClick}
      className="animate-slide-up group flex flex-col rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-5 text-left transition-all duration-300 hover:border-[var(--border-strong)] hover:bg-[var(--bg-tertiary)]"
      style={{ animationDelay: `${0.1 + index * 0.05}s` }}
    >
      <div className="flex items-center gap-3">
        <span
          className={`h-2 w-2 rounded-full ${
            isActive
              ? "bg-[var(--green)] animate-pulse-green"
              : "bg-[var(--text-muted)]"
          }`}
        />
        <span className="text-[14px] font-semibold text-[var(--text-primary)]">
          {node.name}
        </span>
      </div>
      <p
        className="mt-3 text-[12px] text-[var(--text-quaternary)]"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {node.username}@{node.host}:{node.port}
      </p>
      {node.tags && node.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {node.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-md bg-[var(--bg-elevated)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-tertiary)]"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
      <div className="mt-4 flex items-center gap-1.5 text-[11px] text-[var(--text-muted)] transition-colors group-hover:text-[var(--green)]">
        <Terminal size={11} strokeWidth={1.5} />
        <span>View activity</span>
        <span className="ml-auto opacity-0 transition-opacity group-hover:opacity-100">
          →
        </span>
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
    <div className="flex h-full flex-col bg-black">
      {/* Header */}
      <div className="border-b border-[var(--border-subtle)] px-8 py-7">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--green-subtle)]">
            <Command size={15} className="text-[var(--green)]" strokeWidth={1.8} />
          </div>
          <div>
            <h1 className="text-[17px] font-bold tracking-[-0.02em] text-[var(--text-primary)]">
              Overview
            </h1>
            <p className="text-[12px] text-[var(--text-tertiary)]">
              {stats
                ? `${stats.node_count} nodes connected · ${stats.total_commands.toLocaleString()} commands executed`
                : "Loading…"}
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-8 py-7">
        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4">
          <StatCard label="Total Nodes" value={stats?.node_count} icon={Cpu} delay="0s" />
          <StatCard
            label="Active Sessions"
            value={stats?.active_sessions}
            icon={Activity}
            delay="0.05s"
          />
          <StatCard
            label="Commands Executed"
            value={stats?.total_commands}
            icon={Terminal}
            delay="0.1s"
          />
        </div>

        {/* Node grid */}
        <div className="mt-8">
          {nodes.length === 0 ? (
            <div className="animate-fade-in flex flex-col items-center justify-center py-20">
              <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--border-default)] bg-[var(--bg-elevated)]">
                <Server size={24} className="text-[var(--text-quaternary)]" strokeWidth={1.5} />
              </div>
              <p className="text-[15px] font-semibold text-[var(--text-primary)]">
                No nodes configured
              </p>
              <p className="mt-2 text-[13px] text-[var(--text-tertiary)]">
                Add a node to start monitoring SSH activity
              </p>
              <button
                onClick={() => setShowForm(true)}
                className="mt-5 rounded-xl bg-[var(--green)] px-5 py-2.5 text-[13px] font-semibold text-black transition-all duration-200 hover:bg-[var(--green-light)] hover:shadow-[0_0_24px_rgba(118,185,0,0.3)]"
              >
                Add Node
              </button>
            </div>
          ) : (
            <>
              <div className="mb-4 flex items-center justify-between">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-[var(--text-quaternary)]">
                  Nodes
                </p>
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {nodes.map((node, i) => (
                  <NodeCard
                    key={node.id}
                    node={node}
                    onClick={() => navigate(`/activity/${node.id}`)}
                    index={i}
                  />
                ))}
                {/* Add node card */}
                <button
                  onClick={() => setShowForm(true)}
                  className="animate-slide-up flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border-default)] p-5 text-[var(--text-quaternary)] transition-all duration-300 hover:border-[var(--green)]/30 hover:text-[var(--green)]"
                  style={{ animationDelay: `${0.1 + nodes.length * 0.05}s` }}
                >
                  <Plus size={18} strokeWidth={1.5} />
                  <span className="mt-2 text-[12px] font-medium">Add node</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <NodeForm open={showForm} onOpenChange={setShowForm} />
    </div>
  );
}
